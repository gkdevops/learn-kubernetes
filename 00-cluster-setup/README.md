# 00 — Cluster Setup

## Objective
Stand up a Kubernetes cluster to run everything else in this repo.

## Options
| Path | Folder | Best for |
|------|--------|----------|
| AWS EKS (default) | [01-eks](01-eks/) | Production-like, cloud integrations |
| kubeadm | [02-kubeadm](02-kubeadm/) | Understanding the control plane |
| Local | [03-local](03-local/) | Fastest, offline, kind/minikube |

## Prerequisites
- `kubectl` installed.
- Ability to create infrastructure (AWS credentials for EKS) or Docker (for kind).

## Verify
```bash
kubectl get nodes
kubectl get pods -n kube-system
```

## Cleanup
Delete the cluster you created to avoid ongoing cost:
```bash
eksctl delete cluster --region=<region> --name=<name>
```
