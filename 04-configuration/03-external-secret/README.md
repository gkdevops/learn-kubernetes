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
- Secrets Store CSI Driver + AWS provider installed (see [EKS README](../../00-cluster-setup/01-eks/README.md#secrets-store-csi-driver-for-aws-secrets-manager)).
  **Read the `tokenRequests` note there** — without it every mount fails with
  `CSI token error: serviceAccount.tokens not provided`.
- AWS CLI configured

## Two service accounts, not one

This is the part people trip over. On EKS there are **two different identities**
involved, and they are easy to confuse:

| Identity | Who it is | Why |
|----------|-----------|-----|
| `csi-secrets-store-provider-aws` (in `kube-system`) | the provider DaemonSet | its own AWS calls; created by `cluster.yaml` |
| `aws-secrets-demo-sa` (in `default`) | **this Deployment** | the Pod that mounts the secret; IRSA assumes *its* role |

The provider logs the role it is using for every mount, which is the quickest
way to confirm the wiring:

```bash
kubectl logs -n kube-system -l app=csi-secrets-store-provider-aws | grep 'Role ARN'
# Servicing mount request for pod app-with-aws-secrets-... using service
# account aws-secrets-demo-sa ... Role ARN for default:aws-secrets-demo-sa is ...
```

If it instead says `An IAM role must be associated with service account default`,
the Deployment is not using the annotated ServiceAccount.

## 1. Create the secret in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name learn-k8s/demo-creds \
  --secret-string '{"username":"admin","password":"supersecret123"}' \
  --region us-east-1
```

> **The value must be valid JSON.** `jmesPath` is a JSONPath-like query, so
> `{"username":"admin"}` works but `{username:admin}` (no quotes) does not —
> unquoted keys are not JSON and the provider rejects the whole secret:
>
> ```text
> Invalid JSON used with jmesPath in secret: learn-k8s/demo-creds
> Failure getting secret values ...: Failed to fetch secret from all regions.
> Verify secret exists and required permissions are granted for: ...
> ```
>
> That error blames the secret name and permissions even though both are fine,
> which is what makes it confusing. Check what you actually stored with
> `aws secretsmanager get-secret-value --secret-id learn-k8s/demo-creds
> --region us-east-1 --query SecretString --output json` — the quotes must be
> there.
>
> On **PowerShell** the command above silently loses the double quotes when the
> shell hands the argument to the AWS CLI, which produces exactly the broken
> JSON above. Use a file instead:
>
> ```powershell
> '{"username":"admin","password":"supersecret123"}' | Set-Content demo-creds.json
> aws secretsmanager create-secret --name learn-k8s/demo-creds `
>   --secret-string file://demo-creds.json --region us-east-1
> ```

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
>
> If it does *not* recover, read the event rather than guessing — it names the
> real cause:
>
> ```bash
> kubectl describe pod -l app=aws-secrets-demo | grep -A2 FailedToCreateSecret
> # failed to get data in spc ... file matching objectName username not found
> # in the pod
> ```
>
> That message means the volume mounted but the per-key files the
> `secretObjects` block expects are missing — usually because `jmesPath` (or
> `objectAlias`) is absent from the SecretProviderClass, so the provider wrote
> one file for the whole secret instead of one file per key.

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
The `aws-secrets-demo-sa` service account in `default` was created by `eksctl`
with IRSA (IAM Roles for Service Accounts) and carries the
`SecretsManagerReadWrite` policy. The Deployment references it via
`serviceAccountName`, and the AWS provider daemonset uses that identity to fetch
the secret on the Pod's behalf. See
[cluster.yaml](../../00-cluster-setup/01-eks/cluster.yaml).

There is a separate `csi-secrets-store-provider-aws` service account in
`kube-system`, created by the same `cluster.yaml` block. It is easy to assume
that one covers this module — it does not, and using it is what produces
`An IAM role must be associated with service account default`.

> **Least privilege (optional exercise):** `SecretsManagerReadWrite` grants
> access to *every* secret in the account. Replace it with an inline policy
> scoped to this one secret — remembering that Secrets Manager appends a random
> 6-character suffix to the ARN:
>
> ```json
> {
>   "Version": "2012-10-17",
>   "Statement": [{
>     "Effect": "Allow",
>     "Action": ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
>     "Resource": "arn:aws:secretsmanager:us-east-1:<account>:secret:learn-k8s/demo-creds-*"
>   }]
> }
> ```
