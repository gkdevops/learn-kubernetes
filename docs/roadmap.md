# Kubernetes Learning Roadmap

Work top to bottom. Each stage assumes the previous one.

## Stage 0 — Get a cluster
- **[docs/architecture.md](architecture.md)** — read this first: control plane, nodes, reconciliation
- **00-cluster-setup/01-eks** — create an EKS cluster with `eksctl` (default path)
- **00-cluster-setup/02-kubeadm** — self-managed cluster with containerd + Calico
- **00-cluster-setup/03-local** — kind / minikube for a local cluster

## Stage 1 — Fundamentals
- **01-foundations** — namespaces, labels & selectors, multi-resource YAML
- **02-pods** — your first Pod, its lifecycle and `kubectl` verbs

## Stage 2 — Running workloads
- **03-workload-controllers** — ReplicaSet → Deployment → strategies → DaemonSet → Jobs/CronJob

## Stage 3 — Configuring workloads
- **04-configuration** — ConfigMap and Secret consumption (env, envFrom, volume), then AWS Secrets Manager via the Secrets Store CSI driver (IRSA)
- **09-resource-management** — requests/limits, LimitRange, ResourceQuota
- **08-pod-lifecycle** — readiness/liveness probes and lifecycle hooks

## Stage 4 — State
- **05-storage** — emptyDir → hostPath → PV/PVC → StorageClass (dynamic) → EBS CSI

## Stage 5 — Networking
- **06-networking** — ClusterIP → NodePort → LoadBalancer → Gateway API (NGINX Gateway Fabric)

## Stage 6 — Placement & scale
- **07-scheduling** — nodeSelector, node affinity, taints & tolerations
- **11-autoscaling** — Horizontal Pod Autoscaler

## Stage 7 — Operate
- **10-security** — securityContext, non-root
- **12-packaging** — Helm and Kustomize
- **13-observability** — metrics-server, Prometheus, logging

## Coming next (not yet written)
RBAC, NetworkPolicy, StatefulSet, PodDisruptionBudget, VPA &
Cluster Autoscaler, GitOps (Argo CD / Flux), Operators & CRDs, troubleshooting,
and an end-to-end capstone project.

(IRSA is now covered hands-on in `04-configuration/03-external-secret` and
`00-cluster-setup/01-eks`; a dedicated RBAC module is still to come.)
