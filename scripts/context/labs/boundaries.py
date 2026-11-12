"""Offline contracts only. These validators do not qualify or authorize a runner."""

from __future__ import annotations

import configparser
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

HISTORICAL_SHA = "c6021d456bbcce20fec817470aa5237907d7728a"
HISTORICAL_TREE = "925d814b6705ea46c17fed4b75d2788463e1b445"
BINDING_KEYS = (
    "run_id",
    "nonce",
    "request_sha256",
    "subject_commit",
    "subject_tree",
    "execution_handle",
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(
        [
            "git",
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.hooksPath=",
            "-C",
            str(repo),
            *args,
        ],
        capture_output=True,
        check=False,
        timeout=30,
        env={
            **{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        },
    )
    if result.returncode:
        raise ValueError("identity Git query failed")
    return result.stdout


def reject_constant(value: str):
    raise ValueError(f"invalid JSON constant: {value}")


def entry_type(path: Path) -> str:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("unsupported link/reparse point")
    if stat.S_ISDIR(info.st_mode):
        return "directory"
    if stat.S_ISREG(info.st_mode):
        return "file"
    raise ValueError("unsupported filesystem object")


def inventory_tree(root: Path, excluded=(), allowed=None) -> list:
    """No-follow classification; inspection failures propagate and reject validation."""
    if entry_type(root) != "directory":
        raise ValueError("expected directory")
    rows = []

    def visit(directory):
        with os.scandir(directory) as entries:
            paths = sorted((Path(e.path) for e in entries), key=lambda p: p.name)
        for path in paths:
            name = path.relative_to(root).as_posix()
            if name in excluded:
                continue
            kind = entry_type(path)
            if allowed is not None and allowed.get(name) != kind:
                raise ValueError("unexpected path or entry type")
            row = {"path": name, "type": kind}
            if kind == "directory":
                visit(path)
            else:
                raw = path.read_bytes()
                row.update(size=len(raw), sha256=sha(raw))
            rows.append(row)

    visit(root)
    return sorted(rows, key=lambda row: row["path"])


def inventory_digest(rows: list) -> str:
    return sha(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def subject_identity(repo: Path) -> dict:
    """Read actual bytes, including ignored/untracked paths; never refresh the index."""
    metadata = repo / ".git"
    if entry_type(repo) != "directory" or entry_type(metadata) != "directory":
        raise ValueError("private repository directories required")
    objects = inventory_tree(metadata / "objects")
    control = inventory_tree(metadata, excluded=("objects",))
    config = configparser.RawConfigParser()
    try:
        config.read_string((metadata / "config").read_text(encoding="utf-8"))
    except configparser.Error as exc:
        raise ValueError("malformed Git configuration") from exc
    allowed = {
        "repositoryformatversion",
        "filemode",
        "bare",
        "logallrefupdates",
        "symlinks",
        "ignorecase",
        "autocrlf",
        "longpaths",
    }
    if config.sections() != ["core"] or not set(config["core"]) <= allowed:
        raise ValueError("unapproved local Git configuration")
    for name in ("objects/info/alternates", "info/grafts", "config.worktree"):
        if (metadata / name).exists():
            raise ValueError("unsupported alternate/configuration")
    if git(repo, "remote").strip() or git(repo, "replace", "-l").strip():
        raise ValueError("remote or replacement refs")
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all").strip():
        raise ValueError("dirty subject")
    if any(row and row[:1] != b"H" for row in git(repo, "ls-files", "-v", "-z").split(b"\0")):
        raise ValueError("unsupported index flags")
    staged = git(repo, "ls-files", "--stage", "-z")
    if any(row and row.split(b"\t")[0].split()[-1] != b"0" for row in staged.split(b"\0")):
        raise ValueError("unmerged subject")
    tree = git(repo, "rev-parse", "HEAD^{tree}").decode().strip()
    if tree != HISTORICAL_TREE:
        raise ValueError("wrong historical tree")
    tracked = {p.decode("utf-8") for p in git(repo, "ls-files", "-z").split(b"\0") if p}
    allowed_paths = {name: "file" for name in tracked}
    for name in tracked:
        for parent in Path(name).parents:
            if parent != Path("."):
                allowed_paths[parent.as_posix()] = "directory"
    rows = inventory_tree(repo, excluded=(".git",), allowed=allowed_paths)
    inventory = {row["path"]: row["sha256"] for row in rows if row["type"] == "file"}
    if set(inventory) != tracked:
        raise ValueError("missing selected source")
    hooks = metadata / "hooks"
    if hooks.exists() and any(
        p.is_file() and not p.name.endswith(".sample") for p in hooks.iterdir()
    ):
        raise ValueError("unexpected Git hook")
    return {
        "objects_sha256": inventory_digest(objects),
        "metadata_sha256": inventory_digest(control),
        "historical_sha": HISTORICAL_SHA,
        "historical_tree": HISTORICAL_TREE,
        "subject_commit": git(repo, "rev-parse", "HEAD").decode().strip(),
        "subject_tree": tree,
        "inventory": inventory,
        "index_sha256": sha(staged),
        "refs_sha256": sha(git(repo, "show-ref", "--head")),
        "config_sha256": sha((metadata / "config").read_bytes()),
    }


def validate_identity(repo: Path, expected: dict) -> dict:
    if not {"objects_sha256", "metadata_sha256"} <= expected.keys():
        raise ValueError("missing seals; prepare a fresh attempt")
    actual = subject_identity(repo)
    if actual != expected:
        raise ValueError("frozen subject identity mismatch")
    return actual


def validate_terminal(raw: bytes, exit_code: int, expected: dict, observed: dict) -> dict:
    """Conservative CLI event subset; runtime qualification still requires a real smoke."""
    if type(exit_code) is not int or exit_code != 0:
        raise ValueError("unsuccessful execution")
    if not isinstance(expected, dict) or not isinstance(observed, dict):
        raise ValueError("missing controller binding")
    if any(
        not isinstance(expected.get(k), str) or not expected[k] or observed.get(k) != expected[k]
        for k in BINDING_KEYS
    ):
        raise ValueError("controller binding mismatch")
    for key in ("request_sha256", "subject_commit", "subject_tree"):
        size = 64 if key == "request_sha256" else 40
        if len(expected[key]) != size or any(c not in "0123456789abcdef" for c in expected[key]):
            raise ValueError("malformed controller identity")
    if not raw.endswith(b"\n"):
        raise ValueError("truncated event stream")
    events = [
        json.loads(line, object_pairs_hook=unique_object, parse_constant=reject_constant)
        for line in raw.decode("utf-8").split("\n")
        if line.strip()
    ]
    if not events or any(not isinstance(e, dict) for e in events):
        raise ValueError("malformed events")
    thread, started, complete, final = None, False, False, None
    usage = None
    for position, event in enumerate(events):
        kind = event.get("type")
        if kind == "thread.started":
            if (
                position != 0
                or thread is not None
                or not isinstance(event.get("thread_id"), str)
                or not event["thread_id"]
            ):
                raise ValueError("missing/duplicate thread")
            thread = event["thread_id"]
        elif kind == "turn.started":
            if thread is None or started:
                raise ValueError("invalid turn start")
            started = True
        elif kind in {"item.started", "item.updated", "item.completed"}:
            if not started or complete or not isinstance(event.get("item"), dict):
                raise ValueError("invalid item lifecycle")
            item = event["item"]
            if kind == "item.completed" and item.get("type") == "agent_message":
                if not isinstance(item.get("text"), str) or not item["text"].strip():
                    raise ValueError("empty final answer")
                final = item["text"]
        elif kind == "turn.completed":
            if not started or complete or final is None or position != len(events) - 1:
                raise ValueError("missing/duplicate/contradictory completion")
            usage = event.get("usage")
            if not isinstance(usage, dict) or any(
                type(usage.get(k)) is not int or usage[k] < 0
                for k in ("input_tokens", "cached_input_tokens", "output_tokens")
            ):
                raise ValueError("invalid usage")
            if usage["cached_input_tokens"] > usage["input_tokens"]:
                raise ValueError("inconsistent usage")
            if "reasoning_output_tokens" in usage and (
                type(usage["reasoning_output_tokens"]) is not int
                or not 0 <= usage["reasoning_output_tokens"] <= usage["output_tokens"]
            ):
                raise ValueError("invalid reasoning usage")
            complete = True
        else:
            raise ValueError("failure or unsupported event type")
        if "thread_id" in event and event["thread_id"] != thread:
            raise ValueError("wrong thread")
    if not complete:
        raise ValueError("missing terminal event")
    return {
        "binding": expected,
        "thread_id": thread,
        "events_sha256": sha(raw),
        "usage": usage,
        "final_response": final,
        "offline_valid": True,
    }
