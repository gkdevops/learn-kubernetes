# 03 — Workload Controllers

## Objective
Move from bare Pods to controllers that keep workloads running at the desired
state: ReplicaSet, Deployment, DaemonSet, Job and CronJob.

## Prereqs
[02-pods](../02-pods/).

## Examples
| Folder | What it shows |
|--------|---------------|
| [01-replicaset](01-replicaset/) | Maintain N identical Pods |
| [02-deployment](02-deployment/) | Declarative rollouts on top of ReplicaSets |
| [03-strategies](03-strategies/) | RollingUpdate vs Recreate |
| [04-daemonset](04-daemonset/) | One Pod per node |
| [05-jobs-cronjobs](05-jobs-cronjobs/) | Run-to-completion and scheduled work |

## Commands
```bash
kubectl apply -f 01-replicaset/replicaset.yaml
kubectl get rs,pods
kubectl apply -f 02-deployment/deployment.yaml
kubectl rollout status deployment/sales-app
kubectl apply -f 03-strategies/rolling-update.yaml
kubectl apply -f 04-daemonset/daemonset.yaml
kubectl apply -f 05-jobs-cronjobs/job.yaml
kubectl apply -f 05-jobs-cronjobs/cronjob.yaml
```

## Verify
- Deleting a Pod managed by a ReplicaSet makes it reappear.
- `kubectl rollout history deployment/sales-app` shows revisions.
- The DaemonSet creates one Pod per node.

## Cleanup
```bash
kubectl delete -f 01-replicaset/replicaset.yaml -f 02-deployment/deployment.yaml
kubectl delete -f 04-daemonset/daemonset.yaml -f 05-jobs-cronjobs/
```

## Exercise
1. Scale the Deployment to 0 and back — watch the ReplicaSets.
2. Change the rolling-update manifest's `maxSurge`/`maxUnavailable` and observe
   how the rollout behaves.

## EKS note
`initContainers` and Jobs are commonly used for migrations and one-off tasks on EKS.
