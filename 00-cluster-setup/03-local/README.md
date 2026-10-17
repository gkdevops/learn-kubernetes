# 00-cluster-setup / 03 — Local cluster (kind / minikube)

## Objective
Run Kubernetes on your laptop for quick experiments — no cloud required.

## Option A — kind (Kubernetes in Docker)
```bash
kind create cluster --name learn
kubectl cluster-info --context kind-learn
kind delete cluster --name learn
```

## Option B — minikube
```bash
minikube start --nodes 3          # 3 nodes so scheduling demos work
minikube status
minikube delete
```

## Why multiple nodes?
Scheduling lessons ([07-scheduling](../../07-scheduling/)) need more than one
node to be meaningful. `minikube start --nodes 3` or a kind config with several
`nodes` entries gives you that.

## Notes / differences from EKS
- `type: LoadBalancer` Services stay `<pending>` until you enable a load-balancer
  add-on (e.g. `minikube tunnel`, or MetalLB on kind).
- `StorageClass` is `standard` (hostPath-backed), not EBS.
- No IAM/IRSA — cloud-integration lessons need EKS.
