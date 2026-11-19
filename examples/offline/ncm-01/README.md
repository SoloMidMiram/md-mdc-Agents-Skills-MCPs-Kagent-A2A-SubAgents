# NCM-01 offline summarization

Run from the repository root with Python 3.12 or newer.

```powershell
python -m scripts.kagent.experiments.ncm01_worker
python -m scripts.kagent.experiments.ncm01_worker --missing-model
python -m pytest -q tests/kagent/experiments/test_ncm01_worker.py
```

The first command prints deterministic JSON. The fake retains the instruction to
reject a stale digest and request a fresh packet. The extractive baseline takes
the first complete fixture line under its 64-byte demonstration budget. Its
omission of the instruction illustrates why fidelity needs independent checks.
The second command intentionally exits 1 with `missing_model` and empty stdout.

The caller supplies UTF-8 text in memory. Each worker instance admits one call
at a time, with an 8,192-byte input ceiling, a requested output budget of 1 to
512 bytes, and a positive monotonic deadline of at most five seconds. Invalid
inputs and responses are rejected without truncation. A backend must yield to
the event loop and propagate cancellation promptly. Late results are rejected
and the admission slot stays occupied until the call unwinds. The timeout
requests cancellation; the caller may wait past the deadline for cleanup. The
callable owns all work and cleanup for its request. Detached tasks, native
threads, and services require verification of the actual computation lifetime
before a real adapter can release capacity. The smoke command creates no
persistent files or services.

The report records `origin: synthetic`, `capabilityPromotion: false` and a
blocked real run. Hardware, checkpoint identity, transfer size, peak RSS/VRAM
and cold/warm inference latency remain unmeasured. Model acquisition, inference,
provider access and transmission require separate authorization.
