# 10 — Security

## Objective
Harden Pods with `securityContext` and run containers as non-root.

## Prereqs
[02-pods](../02-pods/).

## Examples
| File | What it shows |
|------|---------------|
| [01-securitycontext/nonroot.yaml](01-securitycontext/nonroot.yaml) | `runAsNonRoot`, `runAsUser`, read-only root FS, no privilege escalation |

## Commands
```bash
kubectl apply -f 01-securitycontext/nonroot.yaml
kubectl get pod sample-pod
kubectl exec -it sample-pod -- id
```

## Verify
`id` inside the container reports `uid=1234`. If the image required root to
start, the Pod would fail with a `CreateContainerConfigError`.

## Cleanup
```bash
kubectl delete -f 01-securitycontext/
```

## Exercise
1. Remove `readOnlyRootFilesystem` — can the container now write to `/`?
2. Research Pod Security Admission (`restricted` profile) and which fields it enforces.

## EKS note
Pair `securityContext` with **IRSA** (IAM Roles for Service Accounts) to give
workloads least-privilege AWS access without node-wide instance credentials.
