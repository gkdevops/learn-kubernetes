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
`cluster.yaml` provisions a managed node group, the EBS CSI add-on, and
control-plane logging.

```bash
eksctl create cluster -f cluster.yaml
```

Point `kubectl` at it (eksctl usually does this automatically):

```bash
aws eks update-kubeconfig --name valaxy-eks-cluster --region us-east-1
kubectl get nodes
```

## Add-ons to install next
```bash
# metrics-server (for `kubectl top`) - see 13-observability
kubectl apply -f ../../13-observability/01-metrics-server/metrics-server.yaml
```

## External traffic - NGINX Gateway Fabric

Route external HTTP through the Gateway API, programmed by **NGINX Gateway Fabric**.

### 1. Install the Gateway API CRDs

```bash
kubectl apply --server-side -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.8.0/deploy/crds.yaml
```

(or `kubectl apply -f ../../06-networking/04-gateway-api/crd.yaml`)

### 2. Install NGINX Gateway Fabric

```bash
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --create-namespace -n nginx-gateway

kubectl wait --timeout=5m -n nginx-gateway deployment/ngf-nginx-gateway-fabric --for=condition=Available
```

By default this creates a `LoadBalancer` Service (an AWS **NLB** on EKS).
To use a `NodePort` Service instead:

```bash
helm uninstall ngf -n nginx-gateway
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --create-namespace -n nginx-gateway \
  --set nginx.service.type=NodePort
```

### 3. Verify

```bash
kubectl get pods -n nginx-gateway
kubectl get svc -n nginx-gateway             # external-address of the NGF service
kubectl -n nginx-gateway get deploy ngf-nginx-gateway-fabric
```

Then continue with [06-networking / 04-gateway-api](../../06-networking/04-gateway-api/)
to define a `GatewayClass`, `Gateway` and `HTTPRoute` and route traffic to a demo
app.

## Cleanup
```bash
helm uninstall ngf -n nginx-gateway
kubectl delete -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.8.0/deploy/crds.yaml

eksctl delete cluster --region=us-east-1 --name=valaxy-eks-cluster --force
```

## Next
Continue with [01-foundations](../../01-foundations/).
