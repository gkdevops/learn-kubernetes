# 01 — Foundations

## Objective
Learn the building blocks every other object relies on: namespaces, labels and
selectors, and multi-document YAML.

## Prereqs
A working cluster and `kubectl` (see [00-cluster-setup](../00-cluster-setup/)).

## Examples
| Folder | What it shows |
|--------|---------------|
| [01-namespace](01-namespace/) | Isolate resources with a Namespace |
| [02-multi-resource](02-multi-resource/) | One file, two objects (`---` separated) |

## Commands
```bash
kubectl apply -f 01-namespace/namespace.yaml
kubectl get namespaces
kubectl apply -f 02-multi-resource/singlefile.yaml
kubectl get configmap,deployment
```

## Verify
`kubectl describe namespace development` shows the namespace. The multi-resource
file creates both a ConfigMap (`sales-dev`) and a Deployment (`sales-deployment`).

## Cleanup
```bash
kubectl delete -f 02-multi-resource/singlefile.yaml
kubectl delete -f 01-namespace/namespace.yaml
```

## Exercise
1. Create a namespace `staging`, apply `singlefile.yaml` into it with `-n staging`.
2. Add a `team: platform` label to the namespace and filter with `-l`.
