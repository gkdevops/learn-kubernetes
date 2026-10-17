# 06 — Networking

## Objective
Expose workloads and understand how traffic reaches them: Service types,
Ingress, the Gateway API, and east-west traffic.

## Prereqs
[03-workload-controllers](../03-workload-controllers/).

## Examples
| Folder | What it shows |
|--------|---------------|
| [00-backend-app](00-backend-app/) | Shared nginx + helper Deployment used by the services |
| [01-clusterip](01-clusterip/) | Internal-only Service |
| [02-nodeport](02-nodeport/) | Expose a port on every node |
| [03-loadbalancer](03-loadbalancer/) | Cloud load balancer (AWS NLB on EKS) |
| [05-ingress](05-ingress/) | HTTP routing with the nginx Ingress controller |
| [06-gateway-api](06-gateway-api/) | Gateway API CRDs (the modern successor to Ingress) |

## Commands
```bash
kubectl apply -f 00-backend-app/deployment.yaml
kubectl apply -f 01-clusterip/service.yaml
kubectl apply -f 03-loadbalancer/service.yaml
kubectl get svc -o wide

kubectl apply -f 05-ingress/
kubectl get ingress
```

## Verify
- `ClusterIP` — reachable only from inside the cluster
  (`kubectl run tmp --rm -it --image=busybox -- wget -qO- http://<service>`).
- `NodePort` — reachable on `<node-ip>:<nodePort>`.
- `LoadBalancer` — wait for `EXTERNAL-IP` in `kubectl get svc`.
- `Ingress` — curls to the host/paths defined in `ingress.yaml`.

## Cleanup
```bash
kubectl delete -f 00-backend-app/ -f 01-clusterip/ -f 02-nodeport/ -f 03-loadbalancer/
kubectl delete -f 05-ingress/
```

## Exercise
1. Compare `ClusterIP`, `NodePort` and `LoadBalancer` for the same Deployment.
2. Add a second path to the Ingress and route it to a new Service.

## EKS note
- `type: LoadBalancer` provisions an **AWS NLB** via the AWS cloud provider.
- For ALB Ingress, install the **AWS Load Balancer Controller** and use
  `ingressClassName: alb` with ALB annotations.
- The gateway API requires the respective CRDs (`06-gateway-api/crd.yaml`) to be installed.
