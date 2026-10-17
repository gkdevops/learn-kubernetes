# 09 — Resource Management

## Objective
Reserve and cap CPU/memory with requests and limits, and enforce policy at the
namespace level with LimitRange and ResourceQuota.

## Prereqs
[02-pods](../02-pods/).

## Examples
| File | What it shows |
|------|---------------|
| [01-requests-limits/pod-resources.yaml](01-requests-limits/pod-resources.yaml) | Per-container requests and limits |
| [02-limitrange/limitrange.yaml](02-limitrange/limitrange.yaml) | Namespace defaults and min/max per container |
| [03-resourcequota/resourcequota.yaml](03-resourcequota/resourcequota.yaml) | Namespace-wide hard caps |

## Commands
```bash
kubectl create namespace development
kubectl apply -f 03-resourcequota/resourcequota.yaml -n development
kubectl apply -f 02-limitrange/limitrange.yaml -n development
kubectl apply -f 01-requests-limits/pod-resources.yaml -n development
kubectl describe namespace development          # shows quota usage
```

## Verify
`kubectl describe namespace development` shows `Resource Quota` usage.
Creating a Pod beyond the quota is rejected.

## Cleanup
```bash
kubectl delete -f 01-requests-limits/ -f 02-limitrange/ -f 03-resourcequota/ -n development
kubectl delete namespace development
```

## Exercise
1. Explain what happens when a container has a limit but no request.
2. Set requests == limits ("Guaranteed" QoS) and check `kubectl get pod -o yaml`.

## EKS note
Requests drive node sizing and the Cluster Autoscaler; set them accurately.
