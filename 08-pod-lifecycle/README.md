# 08 — Pod Lifecycle

## Objective
Keep workloads healthy and shut them down gracefully with probes and lifecycle
hooks.

## Prereqs
[03-workload-controllers](../03-workload-controllers/).

## Examples
| Folder | What it shows |
|--------|---------------|
| [01-probes](01-probes/) | Readiness and liveness HTTP probes |
| [02-hooks](02-hooks/) | postStart and preStop lifecycle hooks |

## Commands
```bash
kubectl apply -f 01-probes/deployment-probes.yaml
kubectl get pods -w
kubectl describe pod <pod> | sed -n '/Events/,$p'

kubectl apply -f 02-hooks/deployment-hooks.yaml
kubectl logs <pod>
```

## Verify
- `kubectl describe` shows `Liveness`/`Readiness` probe results.
- Break the liveness path (e.g. point it to `/broken`) and watch the container restart.

## Cleanup
```bash
kubectl delete -f 01-probes/ -f 02-hooks/
```

## Exercise
1. Explain the difference between readiness and liveness failures.
2. Add a `startupProbe` for a slow-starting container.

## EKS note
Set both probes on any internet-facing workload so the NGINX Gateway Fabric /
NLB only sends traffic to healthy Pods.
