"""Validate evidence already received through an independent verifier trust path.

The controller owns the expected binding and time window. Both report and
artifacts must come from the enrolled verifier through authenticated transport
before calling this function. Matching fields cannot authenticate their author.
An accepted bundle is a contract verdict for one phase, never dispatch permission.
"""

import json
import re
from typing import Literal, NamedTuple

from scripts.context.labs.boundaries import reject_constant, sha, unique_object

_DIGEST_FIELDS = ("image_sha256", "configuration_sha256", "runtime_sha256", "request_sha256")
_BINDING_FIELDS = (
    *_DIGEST_FIELDS,
    "nonce",
    "vm_id",
    "execution_id",
    "network_policy_id",
    "credential_mechanism_id",
    "verifier_id",
)

# Probe IDs are also logical artifact keys. No evidence-provided filesystem paths
# are resolved by this validator.
_PROBES = {
    "boundary": {
        "parent_checkout": "denied",
        "historical_repair": "denied",
        "evaluator_assets": "denied",
        "other_experiments": "denied",
        "host_private_data": "denied",
        "unapproved_configuration": "denied",
        "host_mounts_and_devices": "denied",
        "ambient_credentials": "denied",
        "metadata": "denied",
        "public_egress": "denied",
        "private_egress": "denied",
        "link_local_egress": "denied",
        "dns_bypass": "denied",
        "arbitrary_proxy_connect": "denied",
        "inbound_connections": "denied",
        "direct_model_bypass": "denied",
        "unapproved_model_or_provider": "denied",
        "approved_connectivity": "observed",
        "unapproved_mcp_web_and_remotes": "denied",
        "sealed_launch_identity": "observed",
    },
    "teardown": {
        "process_tree_terminated": "observed",
        "vm_and_ephemeral_resources_removed": "observed",
    },
}


class Verdict(NamedTuple):
    status: Literal["ACCEPTED", "BLOCKED"]
    code: str
    evidence: tuple[tuple[str, str], ...] = ()


def verify_qualification(
    *,
    phase: Literal["boundary", "teardown"],
    expected_binding: dict[str, str],
    earliest_observation: int,
    now: int,
    max_age_seconds: int,
    trusted_report: bytes,
    trusted_artifacts: dict[str, bytes],
) -> Verdict:
    """Check one report against controller-owned Unix-second bounds.

    The controller allocates a fresh nonce per attempt and supplies the phase's
    earliest observation time. Repeat validation of the same bundle is idempotent.
    The caller must establish probe execution and meaning through the independent
    trust path, including any authorization needed for the connectivity probe.
    """
    if (
        phase not in _PROBES
        or expected_binding.keys() != set(_BINDING_FIELDS)
        or any(type(value) is not str or not value.strip() for value in expected_binding.values())
        or any(not re.fullmatch(r"[a-f0-9]{64}", expected_binding[k]) for k in _DIGEST_FIELDS)
        or any(type(value) is not int for value in (earliest_observation, now, max_age_seconds))
        or not 0 <= earliest_observation <= now
        or max_age_seconds <= 0
    ):
        return Verdict("BLOCKED", "invalid_controller_expectations")

    try:
        report = json.loads(
            trusted_report.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_constant=reject_constant,
        )
    except (ValueError, RecursionError):
        return Verdict("BLOCKED", "malformed_report")
    if (
        type(report) is not dict
        or report.keys() != {"version", "phase", "binding", "probes"}
        or type(report["version"]) is not int
        or report["version"] != 1
        or report["phase"] != phase
    ):
        return Verdict("BLOCKED", "invalid_envelope")
    if report["binding"] != expected_binding:
        return Verdict("BLOCKED", "binding_mismatch")

    required = _PROBES[phase]
    probes = report["probes"]
    if type(probes) is not dict or probes.keys() != required.keys():
        return Verdict("BLOCKED", "probe_inventory_mismatch")
    if trusted_artifacts.keys() != required.keys():
        return Verdict("BLOCKED", "artifact_inventory_mismatch")

    evidence = []
    earliest = max(earliest_observation, now - max_age_seconds)
    for probe_id, expected_outcome in required.items():
        probe = probes[probe_id]
        if type(probe) is not dict or probe.keys() != {"outcome", "observed_at", "sha256"}:
            return Verdict("BLOCKED", "malformed_probe", ((probe_id, ""),))
        observed_at = probe["observed_at"]
        if type(observed_at) is not int or not earliest <= observed_at <= now:
            return Verdict("BLOCKED", "observation_outside_window", ((probe_id, ""),))
        artifact = trusted_artifacts[probe_id]
        if type(artifact) is not bytes or not artifact or sha(artifact) != probe["sha256"]:
            return Verdict("BLOCKED", "artifact_digest_mismatch", ((probe_id, ""),))
        reference = (probe_id, probe["sha256"])
        if probe["outcome"] != expected_outcome:
            return Verdict("BLOCKED", "unexpected_probe_outcome", (reference,))
        evidence.append(reference)
    return Verdict("ACCEPTED", "evidence_valid", tuple(evidence))
