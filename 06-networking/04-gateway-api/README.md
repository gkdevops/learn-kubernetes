# 04 — Gateway API with NGINX Gateway Fabric

## Objective
Route external HTTP traffic with the **Gateway API** (`gateway.networking.k8s.io`),
programmed by **NGINX Gateway Fabric (NGF)** as the data plane.

## Prerequisites
- A cluster with Gateway API support (Kubernetes 1.31+ for NGF 2.8.0).
- `helm` and `kubectl`.

## Files

| File | What it shows |
|------|---------------|
| [crd.yaml](crd.yaml) | The Gateway API CRDs (v1.5.1 standard bundle) — the API surface itself |
| [http-route.yaml](http-route.yaml) | `GatewayClass` + `Gateway` + `HTTPRoute` routed to the apple/banana demo Services |

## The three objects (and who owns them)

| CRD | Owned by | What it declares |
|-----|----------|------------------|
| `GatewayClass` | platform team | which controller programmes infrastructure (`gateway.nginx.org/nginx-gateway-controller`) |
| `Gateway` | platform team | where traffic enters — listeners, ports, TLS |
| `HTTPRoute` | app team | what host/path goes to which Service |

That platform/app split is the Gateway API's core win over old
annotation-driven workflows.

## Step 1 — Install the Gateway API CRDs

**Recommended (from NGF upstream):**

```bash
kubectl apply --server-side -f https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.8.0/deploy/crds.yaml
```

**Or, offline from this folder:**

```bash
kubectl apply -f crd.yaml
```

## Step 2 — Install NGINX Gateway Fabric

```bash
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --create-namespace -n nginx-gateway
```

Wait for the controller to be Ready before applying routes:

```bash
kubectl wait --timeout=5m -n nginx-gateway deployment/ngf-nginx-gateway-fabric --for=condition=Available
```

Optional — use `NodePort` instead of the default `LoadBalancer` Service
(handy on kind/minikube where no cloud `LoadBalancer` is provisioned):

```bash
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --create-namespace -n nginx-gateway \
  --set nginx.service.type=NodePort
```

## Step 3 — Apply the demo backends and the route

Deploy the demo apple/banana Pods and Services that the route targets:

```bash
kubectl apply -f app.yaml        # apple + banana demo backends
kubectl apply -f http-route.yaml
```

## Verify

```bash
kubectl get gatewayclass,gateway,httproute
kubectl get svc -n nginx-gateway
```

- With NGF running and the CRDs applied, the `Gateway` should report
  `Accepted` and `Programmed`.
- The `HTTPRoute` should report `Accepted`.
- Then (if your HTTPRoute uses hostname `mywebsite.com`):

```bash
curl -H "Host: mywebsite.com" http://<external-address or node-ip>/apple
# -> "welcome to apple"
curl -H "Host: mywebsite.com" http://<external-address or node-ip>/banana
# -> "Welcome to banana"
```

## Cleanup

```bash
kubectl delete -f http-route.yaml
helm uninstall ngf -n nginx-gateway
kubectl delete -f crd.yaml
```

## Exercise
1. Explain who (in a real platform team) would own `GatewayClass`, `Gateway`
   and `HTTPRoute`, and why.
2. Add a `/banana2` HTTPRoute to the same Gateway and observe the routing.
3. Change the Gateway listener to port 8080 and see how the controller reacts.

## EKS note
On EKS the NGF Service becomes an **AWS NLB** (`type: LoadBalancer`, the default)
via the cloud provider. Use `--set nginx.service.type=NodePort` to reach the
Gateway directly through the node IPs instead.
