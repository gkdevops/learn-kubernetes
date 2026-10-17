# 11 — Autoscaling

## Objective
Scale Pods horizontally based on CPU (and other metrics) with the Horizontal
Pod Autoscaler backed by metrics-server.

## Prereqs
[03-workload-controllers](../03-workload-controllers/) and
[13-observability/01-metrics-server](../13-observability/01-metrics-server/).

## Examples
| File | What it shows |
|------|---------------|
| [php-apache-deploy.yaml](01-hpa/php-apache-deploy.yaml) | The target Deployment (with CPU requests) |
| [php-apache-hpa.yaml](01-hpa/php-apache-hpa.yaml) | HPA on `autoscaling/v2` targeting 50% CPU |
| [php-apache-service.yaml](01-hpa/php-apache-service.yaml) | Service for the target |
| [README.md](01-hpa/README.md) | How to generate load |

## Commands
```bash
kubectl apply -f 01-hpa/php-apache-deploy.yaml
kubectl apply -f 01-hpa/php-apache-service.yaml
kubectl apply -f 01-hpa/php-apache-hpa.yaml
kubectl get hpa -w
```

## Verify
With `kubectl get hpa -w` open, generate load in a second terminal (see
[01-hpa/README.md](01-hpa/README.md)). Replica count should climb toward 10,
then settle back to 1 when load stops.

## Cleanup
```bash
kubectl delete -f 01-hpa/
```

## Exercise
1. Why does the HPA need `resources.requests.cpu` on the target?
2. Add a memory metric to the HPA.

## EKS note
HPA scales Pods; pair it with the **Cluster Autoscaler** or **Karpenter** to
add/remove nodes. VPA is an alternative for right-sizing.
