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
# 01 - node selector
kubectl label node <node> disktype=ssd
kubectl apply -f 01-nodeselector/node-selector.yaml
kubectl get pods -o wide     # note the NODE column

# 02 - node affinity (required vs preferred)
kubectl apply -f 02-node-affinity/

# 03 - taints vs tolerations: taint EVERY node, then apply BOTH deployments
for n in $(kubectl get nodes -o name); do
  kubectl taint nodes $n type=2xlarge:NoSchedule
done
kubectl apply -f 03-taints-tolerations/taints.yaml        # tolerates     -> schedules
kubectl apply -f 03-taints-tolerations/deployment.yaml    # no toleration -> Pending
kubectl get pods -o wide
```

> **Taint every node, not just one.** On a multi-node cluster, tainting a
> single node does not make Pods `Pending` - they simply move to a clean node.
> To watch the repelling effect you must taint *all* of them. Verified on this
> course's 2-node cluster: with one node tainted out of two, `untolerated-app`
> still scheduled 2/2 onto the other node.
>
> `NoSchedule` also only affects **new** Pods. Pods that are already running
> stay running, so if you taint after applying, delete them to force
> re-scheduling:
>
> ```bash
> kubectl delete pod -n development -l app=untolerated-app
> ```

## Verify
`kubectl get pods -o wide` shows Pods scheduled only on matching nodes.

For 03 the contrast is the point. `taints.yaml` tolerates `type=2xlarge`, so
its Pods schedule onto the tainted nodes. `deployment.yaml` has no matching
toleration, so its Pods stay `Pending`:

```bash
kubectl describe pod -n development -l app=untolerated-app | tail -3
#   Warning  FailedScheduling  0/2 nodes are available: 2 node(s) had
#   untolerated taint(s). ... preemption: 0/2 nodes are available: 2
#   Preemption is not helpful for scheduling.
```

`kubectl describe pod <name>` shows the scheduling decision and events.

## Cleanup
```bash
kubectl delete -f 01-nodeselector/ -f 02-node-affinity/ -f 03-taints-tolerations/
kubectl label node <node> disktype-
# a trailing minus removes a taint; loop over every node
for n in $(kubectl get nodes -o name); do
  kubectl taint nodes $n type=2xlarge:NoSchedule-
done
```

## Exercise
1. Taint a node with `NoSchedule` and confirm an untolerated Pod stays `Pending`.
2. Compare `requiredDuringScheduling...` vs `preferredDuringScheduling...`.
3. Add a `tolerations` block to `03-taints-tolerations/deployment.yaml` and watch
   its Pods schedule onto the tainted node.

## EKS note
Managed node groups can apply labels and taints automatically; use these to
separate system, GPU, and general workloads.
