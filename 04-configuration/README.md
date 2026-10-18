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
| [03-external-secret/secret-provider-class.yaml](03-external-secret/secret-provider-class.yaml) | SecretProviderClass (AWS Secrets Manager → K8s) |
| [03-external-secret/deployment-secrets-manager.yaml](03-external-secret/deployment-secrets-manager.yaml) | Consume Secrets Manager secret as volume + env vars |

## Commands
```bash
kubectl apply -f 01-configmap/configMap-env.yaml
kubectl apply -f 01-configmap/deployment-env.yaml
kubectl get configmap
kubectl describe configmap sales-dev

kubectl apply -f 02-secret/secret.yaml
kubectl apply -f 02-secret/deployment-secret.yaml
kubectl get secret sales-creds -o jsonpath='{.data.username}' | base64 -d

# EKS only — Secrets Manager example (see 03-external-secret/README.md):
# first create the secret in AWS, then:
kubectl apply -f 03-external-secret/secret-provider-class.yaml
kubectl apply -f 03-external-secret/deployment-secrets-manager.yaml
```

## Verify
`kubectl exec` into a Pod and `env | grep -E 'JAVA_HOME|username'` shows the
injected values.

## Cleanup
```bash
kubectl delete -f 01-configmap/ -f 02-secret/
# for the Secrets Manager example (EKS only):
kubectl delete -f 03-external-secret/
aws secretsmanager delete-secret --secret-id learn-k8s/demo-creds --force-delete-without-recovery --region us-east-1
```

## Exercise
1. Add a second key to `sales-dev` and observe whether a running Pod sees it
   (env vars are fixed at start; mounted files update).
2. Create the same Secret from literals:
   `kubectl create secret generic sales-creds --from-literal=username=admin --from-literal=password=admin123`.

## EKS note
For real secrets, use [03-external-secret](03-external-secret/) which pulls
values from AWS Secrets Manager via the Secrets Store CSI Driver — no
base64-encoded Secrets committed to git.
