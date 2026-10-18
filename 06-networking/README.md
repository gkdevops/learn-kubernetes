# 06 — Networking

## Objective
Expose workloads and understand how traffic reaches them: Service types and the
Gateway API (programmed by NGINX Gateway Fabric).

## Prereqs
[03-workload-controllers](../03-workload-controllers/).

## Examples
| Folder | What it shows |
|--------|---------------|
| [00-backend-app](00-backend-app/) | Shared nginx + helper Deployment used by the Service examples |
| [01-clusterip](01-clusterip/) | Internal-only Service |
| [02-nodeport](02-nodeport/) | Expose a port on every node |
| [03-loadbalancer](03-loadbalancer/) | External load balancer (AWS NLB on EKS) |
| [04-gateway-api](04-gateway-api/) | Gateway API via **NGINX Gateway Fabric** (CRDs + install + Gateway/HTTPRoute) |

## Commands
```bash
kubectl apply -f 00-backend-app/deployment.yaml
kubectl apply -f 01-clusterip/service.yaml
kubectl apply -f 03-loadbalancer/service.yaml
kubectl get svc -o wide
```

## External traffic with NGINX Gateway Fabric

```bash
kubectl apply -f 04-gateway-api/crd.yaml        # Gateway API CRDs (mandatory, before the chart)
helm install ngf oci://ghcr.io/nginx/charts/nginx-gateway-fabric \
  --create-namespace -n nginx-gateway \
  -f 06-networking/04-gateway-api/values.yaml   # NLB + nodePort 30080 -> listener 80
kubectl wait --timeout=5m -n nginx-gateway deployment/ngf-nginx-gateway-fabric --for=condition=Available

kubectl apply -f 04-gateway-api/app.yaml        # demo backends
kubectl apply -f 04-gateway-api/http-route.yaml
kubectl get gateway,httproute
```

Traffic path on EKS: **AWS NLB → worker node :30080 (nodePort) → NGINX data
plane :80 (Gateway listener)**. The data-plane Service is created by NGF when
the `Gateway` is applied, not at helm-install time.

## Verify
- `ClusterIP` — reachable only from inside the cluster
  (`kubectl run tmp --rm -it --image=busybox -- wget -qO- http://<service>`).
- `NodePort` — reachable on `<node-ip>:<nodePort>`.
- `LoadBalancer` — wait for `EXTERNAL-IP` in `kubectl get svc`.
- `Gateway API` — the `Gateway` reports `Accepted` and `Programmed`; curl the
  host/paths defined in `http-route.yaml`.

## Cleanup
```bash
kubectl delete -f 00-backend-app/ -f 01-clusterip/ -f 02-nodeport/ -f 03-loadbalancer/
kubectl delete -f 04-gateway-api/http-route.yaml
helm uninstall ngf -n nginx-gateway
kubectl delete -f 04-gateway-api/crd.yaml
```

## Exercise
1. Compare `ClusterIP`, `NodePort` and `LoadBalancer` for the same Deployment.
2. Add a second path to the HTTPRoute and route it to a new Service.
3. Explain how traffic flows for each Service type.

## EKS note
- `type: LoadBalancer` provisions an **AWS NLB** via the AWS cloud provider.
- The NGINX Gateway Fabric data-plane Service (installed in `04-gateway-api`)
  is pinned to nodePort `30080` → NGINX listener `80`, so external traffic
  flows **NLB → node :30080 → NGINX :80**. On kind/minikube, switch to
  `--set nginx.service.type=NodePort` (same `nodePorts` mapping) and reach
  `<node-ip>:30080` directly.
