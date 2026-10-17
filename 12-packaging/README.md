# 12 — Packaging

## Objective
Package and templatise Kubernetes manifests so the same definition can be
deployed to dev, staging and prod.

## Prereqs
A cluster, plus `helm` and `kustomize` installed.

## Examples
| Folder | What it shows |
|--------|---------------|
| [01-helm](01-helm/) | A Helm chart with a values file per environment |
| [02-kustomize](02-kustomize/) | base + overlays with Kustomize |

## Helm
```bash
helm lint 01-helm
helm template myapp 01-helm
helm install myapp 01-helm -f 01-helm/dev-values.yaml
helm upgrade myapp 01-helm -f 01-helm/prd-values.yaml
helm list
helm uninstall myapp
```

## Kustomize
```bash
kubectl kustomize 02-kustomize/stg      # render
kubectl apply -k 02-kustomize/stg
kubectl kustomize 02-kustomize/prod
```

## Verify
`helm template` / `kubectl kustomize` render the final YAML without applying it —
inspect the differences between environments.

## Cleanup
```bash
helm uninstall myapp
kubectl delete -k 02-kustomize/stg
```

## Exercise
1. Add a `replicaCount: 3` override for prod.
2. In Kustomize, add a `commonLabels` patch and see it propagate.

## EKS note
Helm is the standard way to install cluster add-ons (AWS Load Balancer
Controller, EBS CSI driver, metrics-server, Prometheus).
