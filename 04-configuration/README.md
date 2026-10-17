# 04 — Configuration

## Objective
Externalise configuration and sensitive data from container images using
ConfigMaps and Secrets.

## Prereqs
[02-pods](../02-pods/), [03-workload-controllers](../03-workload-controllers/).

## Examples
| File | What it shows |
|------|---------------|
| [01-configmap/configMap-env.yaml](01-configmap/configMap-env.yaml) | ConfigMap with key/value pairs |
| [01-configmap/deployment-env.yaml](01-configmap/deployment-env.yaml) | Inject individual keys via `configMapKeyRef` |
| [01-configmap/deployment-envFrom.yaml](01-configmap/deployment-envFrom.yaml) | Inject all keys via `envFrom` |
| [01-configmap/deployment-file.yaml](01-configmap/deployment-file.yaml) | Mount a ConfigMap as a file |
| [01-configmap/pod-inline-env.yaml](01-configmap/pod-inline-env.yaml) | Plain env vars (no ConfigMap) |
| [02-secret/secret.yaml](02-secret/secret.yaml) | Secret (base64-encoded) |
| [02-secret/deployment-secret.yaml](02-secret/deployment-secret.yaml) | Consume a Secret as env vars |

## Commands
```bash
kubectl apply -f 01-configmap/configMap-env.yaml
kubectl apply -f 01-configmap/deployment-env.yaml
kubectl get configmap
kubectl describe configmap sales-dev

kubectl apply -f 02-secret/secret.yaml
kubectl apply -f 02-secret/deployment-secret.yaml
kubectl get secret sales-creds -o jsonpath='{.data.username}' | base64 -d
```

## Verify
`kubectl exec` into a Pod and `env | grep -E 'JAVA_HOME|username'` shows the
injected values.

## Cleanup
```bash
kubectl delete -f 01-configmap/ -f 02-secret/
```

## Exercise
1. Add a second key to `sales-dev` and observe whether a running Pod sees it
   (env vars are fixed at start; mounted files update).
2. Create the same Secret from literals:
   `kubectl create secret generic sales-creds --from-literal=username=admin --from-literal=password=admin123`.

## EKS note
For real secrets prefer AWS Secrets Manager with the Secrets Store CSI driver
(or External Secrets Operator) rather than committing Secrets to git.
