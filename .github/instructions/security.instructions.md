---
name: Security review
description: Security expectations for code and infrastructure
applyTo: "**/*.py,**/*.yaml,**/*.yml,**/Dockerfile,**/.github/workflows/*.yml"
---

# Security rules

- Do not hardcode credentials, tokens, or API keys.
- Use environment variables or secret management for sensitive values.
- Validate and sanitize all external input.
- Run `bandit -r src` after modifying security-sensitive Python code.
- Run `trivy fs --scanners vuln,secret,misconfig .` before merging.
- Review dependency changes with `pip-audit`.
- Pin base image digests in Dockerfiles, not just tags.
- Use non-root users in containers.
- Keep the attack surface minimal — do not install unnecessary packages.
