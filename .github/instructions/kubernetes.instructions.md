---
name: Kubernetes quality
description: Safety rules for Kubernetes manifests, Helm and overlays
applyTo: "deploy/**/*.yaml,deploy/**/*.yml,charts/**/*,**/Chart.yaml"
---

# Kubernetes rules

- Never expose a service publicly unless explicitly required.
- Every application container must define CPU and memory requests and limits.
- Use readiness probes for traffic eligibility.
- Use liveness probes only when safe automatic restart behavior is understood.
- Do not store secrets directly in manifests.
- Pin container image tags or digests for production.
- Set a non-root security context where supported.
- Prefer read-only root filesystems where practical.
- Render templates before validation.
- Run kubeconform and kube-linter after changes.
- Record repeated deployment risks in
  `.project-ai/memory/kubernetes-risks.md`.
