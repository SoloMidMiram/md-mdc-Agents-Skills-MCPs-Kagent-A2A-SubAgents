---
name: Test quality
description: Testing expectations and patterns
applyTo: "**/test_*.py,**/*_test.py,tests/**/*.py"
---

# Test rules

- Every public module should have a corresponding test module.
- Name test files `test_<module>.py`.
- Use descriptive test function names explaining the scenario and expectation.
- Prefer pytest fixtures over `setUp`/`tearDown` methods.
- Parametrize tests for multiple input combinations.
- Do not mock external services without a clear isolation boundary.
- Mark slow or integration tests with `@pytest.mark.slow` or `@pytest.mark.integration`.
- Aim for 80%+ coverage on business logic, 60%+ overall.
- Run: `uv run pytest -q` for quick feedback, `uv run pytest --cov=src` for coverage.
