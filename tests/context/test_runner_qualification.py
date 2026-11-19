"""Exercise the evidence contract with synthetic verifier reports."""

import json
from pathlib import Path

import pytest

with pytest.MonkeyPatch.context() as imports:
    imports.syspath_prepend(str(Path(__file__).resolve().parents[2]))
    from scripts.context.labs.boundaries import sha
    from scripts.context.labs.qualification import verify_qualification

DENIAL_PROBES = [
    "parent_checkout",
    "historical_repair",
    "evaluator_assets",
    "other_experiments",
    "host_private_data",
    "unapproved_configuration",
    "host_mounts_and_devices",
    "ambient_credentials",
    "metadata",
    "public_egress",
    "private_egress",
    "link_local_egress",
    "dns_bypass",
    "arbitrary_proxy_connect",
    "inbound_connections",
    "direct_model_bypass",
    "unapproved_model_or_provider",
    "unapproved_mcp_web_and_remotes",
]


def bundle(phase):
    binding = {
        "image_sha256": "a" * 64,
        "configuration_sha256": "b" * 64,
        "runtime_sha256": "c" * 64,
        "request_sha256": "d" * 64,
        "nonce": "attempt-1",
        "vm_id": "vm-1",
        "execution_id": "execution-1",
        "network_policy_id": "deny-default",
        "credential_mechanism_id": "external-model-auth",
        "verifier_id": "independent-verifier",
    }
    outcomes = (
        dict.fromkeys(DENIAL_PROBES, "denied")
        | dict.fromkeys(("approved_connectivity", "sealed_launch_identity"), "observed")
        if phase == "boundary"
        else dict.fromkeys(
            ("process_tree_terminated", "vm_and_ephemeral_resources_removed"), "observed"
        )
    )
    artifacts = {key: f"synthetic {key}: {outcome}".encode() for key, outcome in outcomes.items()}
    report = {
        "version": 1,
        "phase": phase,
        "binding": binding.copy(),
        "probes": {
            key: {"outcome": outcome, "observed_at": 110, "sha256": sha(artifacts[key])}
            for key, outcome in outcomes.items()
        },
    }
    return report, {
        "phase": phase,
        "expected_binding": binding,
        "earliest_observation": 105,
        "now": 120,
        "max_age_seconds": 20,
        "trusted_artifacts": artifacts,
    }


def verify(report, options):
    return verify_qualification(trusted_report=json.dumps(report).encode(), **options)


@pytest.mark.parametrize("phase", ["boundary", "teardown"])
def test_complete_bundle(phase):
    report, options = bundle(phase)
    verdict = verify(report, options)
    assert (verdict.status, verdict.code) == ("ACCEPTED", "evidence_valid")
    assert dict(verdict.evidence) == {
        key: sha(artifact) for key, artifact in options["trusted_artifacts"].items()
    }


@pytest.mark.parametrize(
    "field",
    [
        "nonce",
        "vm_id",
        "execution_id",
        "image_sha256",
        "configuration_sha256",
        "runtime_sha256",
        "request_sha256",
        "network_policy_id",
        "credential_mechanism_id",
        "verifier_id",
    ],
)
def test_bundle_cannot_be_replayed_with_another_binding(field):
    report, options = bundle("boundary")
    options["expected_binding"][field] = "e" * 64
    assert verify(report, options).code == "binding_mismatch"


@pytest.mark.parametrize("observed_at", [99, 104, 121, True, 110.0, "110"])
def test_observation_window_and_types(observed_at):
    report, options = bundle("boundary")
    report["probes"]["metadata"]["observed_at"] = observed_at
    assert verify(report, options).code == "observation_outside_window"


def test_observation_can_expire_within_an_attempt():
    report, options = bundle("boundary")
    options["now"] = 131
    assert verify(report, options).code == "observation_outside_window"


@pytest.mark.parametrize(
    ("phase", "probe", "outcome"),
    [
        ("boundary", "parent_checkout", "readable"),
        ("boundary", "ambient_credentials", "exposed"),
        ("boundary", "public_egress", "reached"),
        ("boundary", "approved_connectivity", "not_run"),
        ("boundary", "approved_connectivity", "failed"),
        ("boundary", "sealed_launch_identity", "mismatch"),
        ("teardown", "process_tree_terminated", "orphaned_after_timeout"),
        ("teardown", "vm_and_ephemeral_resources_removed", "unknown"),
    ],
)
def test_unsuccessful_observations_block(phase, probe, outcome):
    report, options = bundle(phase)
    report["probes"][probe]["outcome"] = outcome
    verdict = verify(report, options)
    assert (verdict.status, verdict.code) == ("BLOCKED", "unexpected_probe_outcome")
    assert verdict.evidence == ((probe, report["probes"][probe]["sha256"]),)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("missing_probe", "probe_inventory_mismatch"),
        ("extra_probe", "probe_inventory_mismatch"),
        ("missing_artifact", "artifact_inventory_mismatch"),
        ("extra_artifact", "artifact_inventory_mismatch"),
        ("tampered_artifact", "artifact_digest_mismatch"),
        ("malformed_probe", "malformed_probe"),
    ],
)
def test_missing_or_tampered_teardown(mutation, code):
    report, options = bundle("teardown")
    probes = report["probes"]
    artifacts = options["trusted_artifacts"]
    key = "vm_and_ephemeral_resources_removed"
    match mutation:
        case "missing_probe":
            del probes[key]
        case "extra_probe":
            probes["extra"] = probes[key]
        case "missing_artifact":
            del artifacts[key]
        case "extra_artifact":
            artifacts["../extra"] = artifacts[key]
        case "tampered_artifact":
            artifacts[key] += b"changed"
        case "malformed_probe":
            del probes[key]["observed_at"]
    assert verify(report, options).code == code


@pytest.mark.parametrize(
    "raw",
    [b"\xff", b"{", b'{"version":1,"version":1}', b'{"probes":{"p":1,"p":2}}', b'{"v":NaN}'],
)
def test_malformed_or_duplicate_json(raw):
    _, options = bundle("boundary")
    assert verify_qualification(trusted_report=raw, **options).code == "malformed_report"


def test_launcher_self_attestation_and_cross_phase_report_block():
    report, options = bundle("boundary")
    assert verify({"qualified": True, "nonce": report["binding"]["nonce"]}, options).status == (
        "BLOCKED"
    )
    options["phase"] = "teardown"
    assert verify(report, options).code == "invalid_envelope"


def test_invalid_controller_window_blocks():
    report, options = bundle("boundary")
    options["max_age_seconds"] = 0
    assert verify(report, options).code == "invalid_controller_expectations"
