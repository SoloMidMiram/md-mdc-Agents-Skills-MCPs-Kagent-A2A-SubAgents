# Offline A2A practice retrospective

The v0.1.0 release met the practice goal by replaying a documentation review
and a coding fixture with offline evidence. The release and replay record are
linked from the [README](../../README.md).

## What the A2A lab taught

A transport response, task dispatch, and terminal completion answer different
questions. The protocol lab checks the wire request ID before accepting a
stream, since the SDK's higher-level response objects reconstruct IDs. A
terminal event and a correlated artifact give the caller concrete evidence
to inspect. The deterministic patch replay adds a worker-process boundary to
that exercise. Its terminal record describes the replay result.

## What the coding lab taught

The coding fixture made the worker output and the evaluator's observations
independently inspectable. A small, fixed input and an explicit acceptance
contract made failures reproducible. The documentation review exercised the
same discipline with source-linked findings. Each runbook gives a maintainer
a way to repeat the result without provisioning a service.

## What to do differently

Define the finish line and the evidence needed before opening the next
implementation issue. Keep one implementation issue active and timebox it.
Refactor when a duplicated contract, observed failure, security need, or
concrete integration consumer gives the change a testable purpose. The
deferred runner, evaluation, and context work can return under its own scope.
