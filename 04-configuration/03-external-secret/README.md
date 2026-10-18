# 04-configuration / 03 — External Secrets (AWS Secrets Manager)

## Objective
Pull secrets from **AWS Secrets Manager** into Pods using the
**Secrets Store CSI Driver** — no more base64-encoded Secrets checked into git.

## How it works

```
AWS Secrets Manager          Secrets Store CSI Driver          Pod
 ┌──────────────┐    ──▶    ┌───────────────────────┐   ──▶  /mnt/secrets/username
 │ learn-k8s/   │           │ SecretProviderClass   │        /mnt/secrets/password
 │  demo-creds  │           │ + synced K8s Secret   │   ──▶  env DB_USERNAME
 └──────────────┘           └───────────────────────┘        env DB_PASSWORD
```

The `SecretProviderClass` tells the CSI driver *which* Secrets Manager secret
to fetch. It also creates a synced Kubernetes Secret (`demo-creds-synced`) so
you can use both **volume mounts** and **env vars**.

## Prereqs
- EKS cluster with OIDC enabled (see [cluster.yaml](../../00-cluster-setup/01-eks/cluster.yaml))
- Secrets Store CSI Driver + AWS provider installed (see [EKS README](../../00-cluster-setup/01-eks/README.md#secrets-store-csi-driver-for-aws-secrets-manager))
- AWS CLI configured

## 1. Create the secret in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name learn-k8s/demo-creds \
  --secret-string '{"username":"admin","password":"supersecret123"}' \
  --region us-east-1
```

## 2. Deploy the SecretProviderClass and the app

```bash
kubectl apply -f secret-provider-class.yaml
kubectl apply -f deployment-secrets-manager.yaml
```

## Verify

### Volume mount (files)
```bash
POD=$(kubectl get pod -l app=aws-secrets-demo -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD -- cat /mnt/secrets/username    # → admin
kubectl exec $POD -- cat /mnt/secrets/password    # → supersecret123
```

### Env vars (from synced K8s Secret)
```bash
kubectl exec $POD -- env | grep DB_
# DB_USERNAME=admin
# DB_PASSWORD=supersecret123
```

> **Heads-up on first apply:** this Pod both mounts the CSI volume *and* reads
> the synced Secret via env vars. The synced `demo-creds-synced` Secret only
> appears after a Pod referencing the `SecretProviderClass` starts — so on the
> very first apply you may see `CreateContainerConfigError` for a short while.
> That's the chicken-and-egg: the pod triggers the sync it depends on. Kubelet
> retries and the Pod recovers on its own; a second rollout (delete the pod) is
> always clean.

### Inspect the synced Secret
```bash
kubectl get secret demo-creds-synced -o jsonpath='{.data.username}' | base64 -d
```

## Cleanup
```bash
kubectl delete -f .
aws secretsmanager delete-secret --secret-id learn-k8s/demo-creds --force-delete-without-recovery --region us-east-1
```

## Exercise
1. Update the secret value in AWS Secrets Manager and observe how long it takes
   for the mounted file to update (the CSI driver polls on a configurable interval).
2. Try removing the `secretObjects` block from the `SecretProviderClass` — what
   happens to the env vars? (They stop working because there is no synced K8s Secret.)

## Comparison: base64 Secret vs Secrets Manager

| | base64 Secret (`02-secret`) | Secrets Manager (this module) |
|---|---|---|
| Where secrets live | In the YAML manifest (git) | In AWS Secrets Manager |
| Encoding | base64 (not encryption) | Encrypted at rest (KMS) |
| Rotation | Manual `kubectl apply` | Update in AWS, CSI driver picks it up |
| Access control | K8s RBAC | IAM policies + K8s RBAC |
| Best for | Local/dev clusters | EKS / cloud environments |

## EKS note
The `csi-secrets-store-provider-aws` service account in `kube-system` was
created by `eksctl` with IRSA (IAM Roles for Service Accounts) and carries the
`SecretsManagerReadWrite` policy — the AWS provider daemonset uses it to fetch
secrets on behalf of your Pods. See
[cluster.yaml](../../00-cluster-setup/01-eks/cluster.yaml).
