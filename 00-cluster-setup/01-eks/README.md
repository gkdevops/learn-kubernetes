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

## Create the cluster
`cluster.yaml` provisions a managed node group, the EBS/EFS CSI add-ons,
an OIDC provider (for IRSA), a Secrets Manager service account, and
control-plane logging.

```bash
eksctl create cluster -f cluster.yaml
```

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
  --set enableSecretRotation=true
```

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
Gateway HTTP listener on port **80**:

```bash
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --create-namespace -n nginx-gateway \
  --set nginx.service.type=LoadBalancer \
  --set-json 'nginx.service.nodePorts=[{"port":30080,"listenerPort":80}]'

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
