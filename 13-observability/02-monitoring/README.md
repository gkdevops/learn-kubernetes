# 13-observability / 02 — Monitoring (Prometheus)

## Objective
Install the Prometheus monitoring stack via Helm and inspect cluster/resource
metrics in its UI.

## Prerequisites
- An EKS cluster with the EBS CSI driver (Prometheus persists data on a volume).
- `helm` configured.

## Commands
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm upgrade -i prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace \
  --set alertmanager.persistence.storageClass="gp2" \
  --set server.persistentVolume.storageClass="gp2"
```

## Verify
```bash
kubectl get pods -n monitoring
```
Open the UI locally (server default is unauthenticated - port-forward instead
of exposing it):

```bash
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
# browse http://localhost:9090, e.g. query: rate(container_cpu_usage_seconds_total[5m])
```

## Cleanup
```bash
helm uninstall prometheus -n monitoring
kubectl delete namespace monitoring
```

## Exercise
1. Query `kube_pod_container_status_waiting_reason` and explain the reasons you see.
2. Add Grafana to the same namespace and point it at the Prometheus data source.

## EKS note
Prometheus needs IAM for nothing (it reads kube-apiserver metrics via a token),
but persistent `gp2` volumes require the EBS CSI driver to be installed
(see `00-cluster-setup/01-eks/`).
