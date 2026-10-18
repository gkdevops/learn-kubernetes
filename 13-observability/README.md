# 13 — Observability

## Objective
See what your cluster is doing: metrics, dashboards, and logs.

## Prereqs
A cluster and `kubectl`.

## Examples
| Folder | What it shows |
|--------|---------------|
| [01-metrics-server](01-metrics-server/) | Install metrics-server (`kubectl top`) |
| [02-monitoring](02-monitoring/) | Prometheus via Helm |
| [03-logging](03-logging/) | Centralised logging with Fluent Bit → Elasticsearch |

## Metrics
```bash
kubectl apply -f 01-metrics-server/metrics-server.yaml
kubectl top nodes
kubectl top pods -A
```

## Monitoring (Prometheus)
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade -i prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace \
  --set alertmanager.persistence.storageClass=ebs-sc \
  --set server.persistentVolume.storageClass=ebs-sc
```

## Logging
See [03-logging/README.md](03-logging/README.md) for the ELK / Fluent Bit stack
(Elasticsearch, Kibana, Fluent Bit).

## Cleanup
```bash
kubectl delete -f 01-metrics-server/metrics-server.yaml
helm uninstall prometheus -n monitoring
```

## Exercise
1. Why does `kubectl top` fail until metrics-server is running?
2. Ship container logs to CloudWatch Logs instead of Elasticsearch.

## EKS note
Enable **EKS control-plane logging** (audit, authenticator, controllerManager)
and use CloudWatch Logs Insights, or run the CloudWatch agent for node logs.
