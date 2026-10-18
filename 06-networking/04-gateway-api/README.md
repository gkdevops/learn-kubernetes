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
| [nginx-crds.yaml](nginx-crds.yaml) | The 14 `gateway.nginx.org` CRDs the NGF chart needs (vendored from v2.8.0) |
| [values.yaml](values.yaml) | Helm values: NLB Service + nodePort 30080→80 mapping + client-IP rewriting |
| [http-route.yaml](http-route.yaml) | `GatewayClass` + `Gateway` + `HTTPRoute` routed to the apple/banana demo Services |

## The three objects (and who owns them)

| CRD | Owned by | What it declares |
|-----|----------|------------------|
| `GatewayClass` | platform team | which controller programmes infrastructure (`gateway.nginx.org/nginx-gateway-controller`) |
| `Gateway` | platform team | where traffic enters — listeners, ports, TLS |
| `HTTPRoute` | app team | what host/path goes to which Service |

That platform/app split is the Gateway API's core win over old
annotation-driven workflows.

## Step 1 — Install both CRD sets

There are **two** CRD bundles here and you need **both**. They are not
alternatives to each other:

| File | CRDs | Needed by |
|------|------|-----------|
| `crd.yaml` | 8 standard Gateway API (`gateway.networking.k8s.io`) | `http-route.yaml` — `Gateway`, `GatewayClass`, `HTTPRoute` |
| `nginx-crds.yaml` | 14 NGINX-specific (`gateway.nginx.org`) | the NGF chart itself — `NginxGateway`, `NginxProxy` |

Install them in this order:

```bash
kubectl apply --server-side -f crd.yaml
kubectl apply --server-side -f nginx-crds.yaml
```

> `--server-side` is recommended for large CRDs: client-side apply stores the
> whole CRD in the `last-applied-configuration` annotation, and these bundles are
> big enough to hit the 256 KB annotation limit.

Skipping either one fails with a message that points at the wrong thing:

```text
# nginx-crds.yaml missing -> at `helm install ngf`
no matches for kind "NginxGateway" in version "gateway.nginx.org/v1alpha1"

# crd.yaml missing -> at `kubectl apply -f http-route.yaml`
no matches for kind "GatewayClass" in version "gateway.networking.k8s.io/v1"
```

To refresh the vendored copy from upstream instead of using the file in this
folder:

```bash
curl -O https://raw.githubusercontent.com/nginx/nginx-gateway-fabric/v2.8.0/deploy/crds.yaml
```

## Step 2 — Install NGINX Gateway Fabric

On EKS we want an **AWS NLB** in front of the data plane, forwarding to the
worker nodes on **port 30080**, which maps to port **80** (the HTTP Gateway
listener) on the NGINX data plane:

```text
internet → AWS NLB → worker node :30080 (nodePort) → NGINX data plane :80
```

One Service does the whole chain: NGF creates the data-plane Service as
`type: LoadBalancer` (EKS provisions the NLB), and we pin its nodePort to
`30080` mapped to the Gateway listener port `80`. Both live in
[values.yaml](values.yaml):

```bash
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --create-namespace -n nginx-gateway \
  -f 06-networking/04-gateway-api/values.yaml
```

Wait for the controller to be Ready before applying routes:

```bash
kubectl wait --timeout=5m -n nginx-gateway deployment/ngf-nginx-gateway-fabric --for=condition=Available
```

> On kind/minikube (no cloud load balancer), skip the NLB and override the
> Service type with `--set nginx.service.type=NodePort` (same `nodePorts`
> mapping), then reach the Gateway directly on `<node-ip>:30080`.

## Step 3 — Apply the demo backends and the route

Deploy the demo apple/banana Pods and Services, then the route:

```bash
kubectl apply -f app.yaml        # apple + banana demo backends
kubectl apply -f http-route.yaml
```

**Important:** the NGINX data-plane Service (`LoadBalancer`/`NodePort`) is
created by NGF **when the first `Gateway` is applied** — not at helm-install
time (helm only creates the control-plane Service, which is ClusterIP-only).

## Verify

```bash
kubectl get gatewayclass,gateway,httproute
kubectl get svc -n nginx-gateway
```

- The `Gateway` should report `Accepted` and `Programmed`; the `HTTPRoute`
  should report `Accepted`.
- After the `Gateway` is applied, NGF creates the data-plane Service — check
  that it is `type: LoadBalancer` with `port 80/nodePort 30080`:

```bash
kubectl get svc -n nginx-gateway -o wide
# ngf-nginx-...   LoadBalancer   ...   80:30080/TCP
```

- The AWS NLB's hostname appears in `EXTERNAL-IP` once provisioning finishes
  (takes a couple of minutes).
- Then (if your HTTPRoute uses hostname `mywebsite.com`):

```bash
curl -H "Host: mywebsite.com" http://<nlb-hostname or node-ip>:30080/apple
# -> "welcome to apple"
curl -H "Host: mywebsite.com" http://<nlb-hostname or node-ip>:30080/banana
# -> "Welcome to banana"
```

## Cleanup

```bash
kubectl delete -f http-route.yaml
helm uninstall ngf -n nginx-gateway
kubectl delete -f nginx-crds.yaml
kubectl delete -f crd.yaml
```

## Exercise
1. Explain who (in a real platform team) would own `GatewayClass`, `Gateway`
   and `HTTPRoute`, and why.
2. Add a `/banana2` HTTPRoute to the same Gateway and observe the routing.
3. Change the Gateway listener to port 8080 and see how the controller reacts.

## EKS note
- The pinned nodePort (`30080` → listener `80`) is applied to the data-plane
  Service even with `type: LoadBalancer`, so the EKS cloud provider builds an
  **AWS NLB** whose instance targets forward to `node:30080` and on to NGINX
  on port `80` — no AWS Load Balancer Controller needed.
- NGF sets `externalTrafficPolicy: Local` by default, which preserves the
  client source IP; the NLB health check only marks nodes running an NGF data
  plane Pod as healthy.
- `values.yaml` also configures client-IP rewriting (`XForwardedFor`): NGINX
  trusts the addresses in `trustedAddresses` when reading the real client IP.
  The CIDR there **must match your VPC** (`10.0.0.0/16` is the default for
  `eksctl`-created VPCs in this repo — adjust if yours differs).
- On kind/minikube use `--set nginx.service.type=NodePort` with the same
  `nodePorts` mapping and reach `<node-ip>:30080` directly.
