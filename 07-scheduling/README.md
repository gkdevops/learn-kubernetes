# 07 — Scheduling

## Objective
Control where Pods land in the cluster using node selectors, affinity, and
taints/tolerations.

## Prereqs
A multi-node cluster (or several nodes simulated with kind).

## Examples
| Folder | What it shows |
|--------|---------------|
| [01-nodeselector](01-nodeselector/) | Simple `nodeSelector` match |
| [02-node-affinity](02-node-affinity/) | Required vs preferred node affinity |
| [03-taints-tolerations](03-taints-tolerations/) | Taints repel Pods; tolerations allow them |

## Commands
```bash
kubectl label node <node> disktype=ssd
kubectl apply -f 01-nodeselector/node-selector.yaml
kubectl apply -f 02-node-affinity/
kubectl apply -f 03-taints-tolerations/taints.yaml
kubectl get pods -o wide     # note the NODE column
```

## Verify
`kubectl get pods -o wide` shows Pods scheduled only on matching nodes.
`kubectl describe pod <name>` shows the scheduling decision and events.

## Cleanup
```bash
kubectl delete -f 01-nodeselector/ -f 02-node-affinity/ -f 03-taints-tolerations/
kubectl label node <node> disktype-
```

## Exercise
1. Taint a node with `NoSchedule` and confirm an untolerated Pod stays `Pending`.
2. Compare `requiredDuringScheduling...` vs `preferredDuringScheduling...`.

## EKS note
Managed node groups can apply labels and taints automatically; use these to
separate system, GPU, and general workloads.
