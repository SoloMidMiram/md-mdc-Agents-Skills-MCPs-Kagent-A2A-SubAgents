# E3 supplied-bundle documentation validator

The educational docs agent reviews explicitly supplied documentation through the existing A2A example runner. The sample uses the established LiteLLM model configuration and has no tools. Document text is untrusted input.

Supply a UTF-8 JSON object containing `schemaVersion` (`"1.0"`), a nonempty `bundleId`, and `files`. Each file contains a normalized relative POSIX `path`, exact `content`, and lowercase `sha256` of its UTF-8 contents. Limits are 16 files, 32 KiB per file, and 128 KiB total. The caller is responsible for selecting and sanitizing the files.

In an authorized environment, invoke the shared runner with an explicitly supplied bundle:

```sh
python scripts/kagent/experiments/run_a2a_example.py --agent docs-agent --prompt-file bundle.json
```

The runner verifies the input before discovery or dispatch. It requires exact JSON output with `summary`, `findings`, `passedChecks`, and `unresolvedQuestions`. Each finding cites an existing path and inclusive one-based lines, with the exact excerpt including line endings. A missing-target finding cites the source reference. Unsupported and contradicted claims have separate categories. Citation verification establishes grounding in the supplied text. External facts and the interpretation of cited text remain outside deterministic verification.

The generic evidence recorder requires the source bundle to reverify citations and therefore rejects standalone E3 success records. Use the offline tests to exercise the validation boundary without an agent or model.
