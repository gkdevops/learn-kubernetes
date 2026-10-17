# Learn Kubernetes

A hands-on, example-driven Kubernetes course. Every topic lives in its own
numbered module with runnable manifests, the exact commands to apply them, and
how to verify and clean up.

The examples target an **AWS EKS cluster by default** (they also work on any
CNCF-conformant cluster, and notes call out where local clusters differ).
See [docs/roadmap.md](docs/roadmap.md) for the full learning path.

## Prerequisites

- A Kubernetes cluster. The fastest path on AWS is [`eksctl`](00-cluster-setup/01-eks/) —
  see the module README. For a local cluster you can use kind or minikube.
- `kubectl` configured against that cluster (`kubectl get nodes` should work).
- Optional tooling: `helm`, `kustomize`, `eksctl`, `aws` CLI.

## How to use this repo

1. Work through the modules in order — they are numbered by learning progression.
2. Read each module's `README.md` (objective → commands → verify → cleanup → exercise).
3. Apply the manifests, inspect the result with `kubectl`, then clean up.
4. Fix nothing blindly: the point is to observe behaviour and predict it.

Each module README ends with an **Exercise** and, where relevant, an **EKS note**.

## Modules

| # | Module | What you learn |
|---|--------|----------------|
| 00 | [cluster-setup](00-cluster-setup/) | Create a cluster: EKS (default), kubeadm, kind/minikube |
| 01 | [foundations](01-foundations/) | Namespaces, labels/selectors, multi-resource files |
| 02 | [pods](02-pods/) | The atom of Kubernetes: a single Pod |
| 03 | [workload-controllers](03-workload-controllers/) | ReplicaSet, Deployment, strategies, DaemonSet, Jobs/CronJob |
| 04 | [configuration](04-configuration/) | ConfigMaps and Secrets |
| 05 | [storage](05-storage/) | emptyDir, hostPath, PV/PVC (static), StorageClass (dynamic), EBS CSI |
| 06 | [networking](06-networking/) | ClusterIP, NodePort, LoadBalancer, Ingress, Gateway API |
| 07 | [scheduling](07-scheduling/) | nodeSelector, node affinity, taints & tolerations |
| 08 | [pod-lifecycle](08-pod-lifecycle/) | Liveness/readiness probes, lifecycle hooks |
| 09 | [resource-management](09-resource-management/) | requests/limits, LimitRange, ResourceQuota |
| 10 | [security](10-security/) | securityContext and running as non-root |
| 11 | [autoscaling](11-autoscaling/) | Horizontal Pod Autoscaler with metrics-server |
| 12 | [packaging](12-packaging/) | Helm charts and Kustomize overlays |
| 13 | [observability](13-observability/) | metrics-server, Prometheus monitoring, logging |

## Validate the manifests

CI runs [kubeconform](https://github.com/yannh/kubeconform) on every push. To run it locally:

```bash
bash scripts/validate.sh
```

## Reference

- [kubectl cheat sheet](docs/kubectl-cheatsheet.md)
- [Good articles](docs/good-articles.md)
- [Roadmap](docs/roadmap.md)

## License

[MIT](LICENSE)
