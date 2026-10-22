# 00-cluster-setup / 01 — EKS (default)

## Objective
Create a production-like Kubernetes cluster on AWS with `eksctl`.

## Prerequisites
1. Install the [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
2. Configure credentials:
   ```bash
   export AWS_ACCESS_KEY_ID=...
   export AWS_SECRET_ACCESS_KEY=...
   export AWS_DEFAULT_REGION=us-east-1
   ```
3. Install [`eksctl`](https://eksctl.io/installation/).
4. Make sure your SSH public key exists at `~/.ssh/aws.pub`
   (the public half of the key you use to log in to EC2 instances).
   eksctl only needs the **public** key; derive it from an existing private
   key instead of generating a new pair:

   ```bash
   ssh-keygen -y -f /path/to/private.pem > ~/.ssh/aws.pub
   ```

   On Windows, also strip the group/other ACLs from the `.pem` or `ssh`
   refuses it with `UNPROTECTED PRIVATE KEY FILE`:

   ```powershell
   icacls myaws.pem /remove:g "BUILTIN\Users" "NT AUTHORITY\Authenticated Users"
   ```

## Create the cluster
`cluster.yaml` provisions a managed node group, the EBS/EFS CSI add-ons,
an OIDC provider (for IRSA), a Secrets Manager service account, and
control-plane logging.

```bash
eksctl create cluster -f cluster.yaml
```

### The `vpc` block is pinned to this account's subnets

`cluster.yaml` reuses an existing VPC instead of letting eksctl create one,
because the default VPC has **no NAT gateway**:

```
vpc-0ef81059ce16ee1e2  172.31.0.0/16
  us-east-1a  subnet-05683e137491c80c0  public
  us-east-1b  subnet-0cad1fcc0ff77c377  public
```

> **Why this matters.** With no `vpc` block, eksctl creates a new VPC and puts
> nodes in the **private** subnets, which have no route to the internet — every
> image pull then fails with `ImagePullBackOff`. You would need a NAT gateway
> (~$32/month) or ECR/S3 VPC endpoints to fix it. Public subnets get the same
> internet access for free, which is why a learning cluster should use them.

> **Pin it in the YAML, not on the command line.** eksctl refuses to combine a
> config file with subnet flags:
> `Error: cannot use --vpc-public-subnets when --config-file/-f is set`.
> There is also no `--vpc-id` flag, and `--vpc-nat-mode` is rejected alongside
> `-f` as well.

If you run this in a different account, replace the two subnet IDs (and the
`ssh.publicKeyPath`) with your own, or delete the whole `vpc:` block and accept
the NAT gateway cost.

Verify the nodes really do have internet access:

```bash
kubectl get nodes -o wide
kubectl run netcheck --rm -it --restart=Never --image=busybox:1.36 -- \
  wget -qO- -T5 https://registry.k8s.io/v2/ ; echo "exit=$?"
```

A non-zero `wget` exit (401/403 from the registry) still proves egress works;
an `ImagePullBackOff` on the `netcheck` pod does not.

### Check the node group has room for Pods

The second thing that breaks a fresh cluster is Pod capacity. Check it explicitly:

```bash
kubectl get nodes -o custom-columns=NAME:.metadata.name,PODCAP:.status.allocatable.pods
kubectl get pods -A --field-selector spec.nodeName=<node> --no-headers | wc -l
```

With the original `t3.small` / `t2.small` node group, EKS gives each node
**8 Pod slots** — and the six add-ons consume exactly 8:

```
aws-node + coredns + kube-proxy + ebs-csi-controller + ebs-csi-node
+ efs-csi-controller + efs-csi-node + metrics-server  =  8/8
```

Both nodes then sit at 100% with **zero** application Pods, and your first
`kubectl run` fails with a message that never mentions capacity:

```
0/2 nodes are available: 2 Too many pods.
```

`cluster.yaml` sets `maxPodsPerNode: 30` to avoid this. Two caveats worth knowing:

- **You cannot raise it later.** AWS treats a managed node group's `maxPods` as
  immutable, so changing it means creating a *new* node group and deleting the
  old one.
- 30 slots on a `t3.medium` still needs real `requests` in your manifests; 30
  Pods each asking for 100Mi memory will exhaust 4 GB on their own. See
  [09-resource-management](../09-resource-management/).

### Spot vs on-demand

The node group here is on-demand (`spot: false`). Spot is roughly 70% cheaper,
but AWS can reclaim an instance with only a **2-minute** warning. During a lab
that evicts the Pod you are testing at the worst moment, and the resulting
`CrashLoopBackOff` / `NotReady` looks exactly like a broken manifest. On-demand
also avoids "insufficient Spot capacity" when a single AZ is saturated. For a
throwaway learning cluster the small extra cost is worth the predictability.

Point `kubectl` at it (eksctl usually does this automatically):

```bash
aws eks update-kubeconfig --name learn-k8s --region us-east-1
kubectl get nodes
```

## Add-ons to install next
```bash
# metrics-server (for `kubectl top`) - see 13-observability
kubectl apply -f ../../13-observability/01-metrics-server/metrics-server.yaml
```

## Secrets Store CSI Driver (for AWS Secrets Manager)

The **Secrets Store CSI Driver** lets Pods mount secrets from AWS Secrets
Manager as volumes, avoiding base64-encoded Secrets in git.

### 1. Install the CSI driver

```bash
helm repo add secrets-store-csi-driver https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
  --namespace kube-system \
  --set syncSecret.enabled=true \
  --set enableSecretRotation=true \
  --set tokenRequests[0].audience=sts.amazonaws.com \
  --set tokenRequests[1].audience=pods.eks.amazonaws.com
```

> **`tokenRequests` is not optional with an IRSA-based provider.** The AWS
> provider needs a projected ServiceAccount token so it can call
> `sts:AssumeRoleWithWebIdentity` *as the workload Pod's identity*. The chart
> defaults `tokenRequests: []`, so without those two flags every mount fails
> with:
>
> ```text
> MountVolume.SetUp failed: CSI token error: serviceAccount.tokens not provided
> - ensure tokenRequests is configured in CSIDriver spec
> ```
>
> You can read the exact audiences the provider wants from its own log:
> `This provider requires tokenRequests to be configured in the CSIDriver spec
> (audiences: sts.amazonaws.com, pods.eks.amazonaws.com)`.

`syncSecret.enabled=true` lets the driver create a mirrored K8s Secret so you
can also use `secretKeyRef` in env vars (not just volume mounts).

> **IAM note:** the component that actually calls AWS is the **AWS provider
> daemonset**, which runs as the service account `csi-secrets-store-provider-aws`
> in `kube-system`. `cluster.yaml` creates that service account with IRSA and the
> `SecretsManagerReadWrite` policy at cluster-creation time; installing the
> provider below preserves that annotation. Confirm it before going further:

```bash
kubectl describe sa csi-secrets-store-provider-aws -n kube-system | grep role-arn
```

### 2. Install the AWS provider (ASCP)

```bash
kubectl apply -f https://raw.githubusercontent.com/aws/secrets-store-csi-driver-provider-aws/main/deployment/aws-provider-installer.yaml
```

### 3. Verify

```bash
kubectl get pods -n kube-system -l app=secrets-store-csi-driver
kubectl get pods -n kube-system -l app=csi-secrets-store-provider-aws
kubectl get csidriver secrets-store.csi.k8s.io
```

Then continue with [04-configuration / 03-external-secret](../../04-configuration/03-external-secret/)
to create a secret in AWS Secrets Manager and consume it from a Pod.

## External traffic - NGINX Gateway Fabric

Route external HTTP through the Gateway API, programmed by **NGINX Gateway Fabric**.

### 1. Install the Gateway API CRDs (mandatory, before the Helm chart)

NGINX Gateway Fabric requires the Gateway API resources to be present in the
cluster **before** its Helm chart is deployed:

```bash
kubectl apply --server-side -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.8.0/deploy/crds.yaml
```

(or `kubectl apply -f ../../06-networking/04-gateway-api/crd.yaml`)

### 2. Install NGINX Gateway Fabric

Install with the data-plane Service pinned to nodePort **30080** mapped to the
Gateway HTTP listener on port **80** (see
[06-networking/04-gateway-api/values.yaml](../../06-networking/04-gateway-api/values.yaml)):

```bash
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --create-namespace -n nginx-gateway \
  -f ../../06-networking/04-gateway-api/values.yaml

kubectl wait --timeout=5m -n nginx-gateway deployment/ngf-nginx-gateway-fabric --for=condition=Available
```

On EKS this gives the traffic path: **AWS NLB → worker node :30080 → NGINX
data plane :80**.

To use a plain `NodePort` Service (local/kind clusters, no NLB), swap
`--set nginx.service.type=LoadBalancer` for `--set nginx.service.type=NodePort`
and keep the same `nodePorts` mapping.

### 3. Verify

```bash
kubectl get pods -n nginx-gateway
kubectl -n nginx-gateway get deploy ngf-nginx-gateway-fabric
```

Note: the NGINX data-plane Service (the `LoadBalancer` that becomes the AWS
NLB) is created **after a `Gateway` resource is applied** — not at
helm-install time. Check it once you've routed traffic via
[06-networking / 04-gateway-api](../../06-networking/04-gateway-api/):

```bash
kubectl get svc -n nginx-gateway     # 80:30080/TCP, EXTERNAL-IP = NLB hostname
```

Then continue with [06-networking / 04-gateway-api](../../06-networking/04-gateway-api/)
to define a `GatewayClass`, `Gateway` and `HTTPRoute` and route traffic to a demo
app.

## Cleanup
```bash
helm uninstall ngf -n nginx-gateway
kubectl delete -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.8.0/deploy/crds.yaml

eksctl delete cluster --region=us-east-1 --name=learn-k8s --force
```

## Next
Continue with [01-foundations](../../01-foundations/).
