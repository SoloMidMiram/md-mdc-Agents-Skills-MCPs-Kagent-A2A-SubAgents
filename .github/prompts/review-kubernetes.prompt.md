# Review Kubernetes Prompt

Run this when reviewing Kubernetes manifest changes.

1. Render any Helm or Kustomize templates fully.
2. Run `kubeconform -strict -summary deploy/`.
3. Run `kube-linter lint deploy/`.
4. Check that every container has CPU and memory requests and limits.
5. Check that readiness probes are configured for HTTP services.
6. Verify no secrets are inlined in manifests.
7. Verify non-root security context is set.

Report:
- Files reviewed
- Validation results (kubeconform, kube-linter)
- Any risks found
