# 05 — Gateway API

## Objective
Meet the successor to Ingress: the `gateway.networking.k8s.io` API. The CRDs in
[crd.yaml](crd.yaml) (Gateway API v1.5.1 standard bundle) define `GatewayClass`,
`Gateway`, `HTTPRoute`, and related policies like `BackendTLSPolicy`.

## What makes it different from Ingress

| | Ingress | Gateway API |
|--|---------|-------------|
| Role-boundary | annotations do everything (controller-specific) | `GatewayClass` (who), `Gateway` (where), `HTTPRoute` (what) |
| Who owns what | app team writes Ingress that also configures the LB | platform team owns Gateway, app team owns HTTPRoute |
| Protocol support | HTTP/1 only, via annotations for the rest | HTTP/2, TLS, TCP, UDP, GRPC are first-class |

## Files

| File | What it shows |
|------|---------------|
| [crd.yaml](crd.yaml) | The Gateway API CRDs installed into the cluster |
| [http-route.yaml](http-route.yaml) | A `GatewayClass`, `Gateway` and `HTTPRoute` routed to the apple/banana demo Services |

## Installing an implementation
CRDs alone do not programme traffic — you need a controller that reads them. For
the nginx Gateway Fabric used by `crd.yaml`:

```bash
kubectl apply -f crd.yaml          # CRDs first
helm install ngf nginx-gateway-fabric --repo https://helm.nginx.com/nginx-gateway-fabric
kubectl apply -f http-route.yaml
```

(EKS alternative: the AWS Gateway API Controller for VPC Lattice.)

## Verify

```bash
kubectl apply -f 04-ingress/app.yaml     # apple + banana demo backends
kubectl apply -f http-route.yaml

kubectl get gatewayclass,gateway,httproute
kubectl get gateway my-gateway -o jsonpath='{.status.conditions[*].type}'
# requires an installed controller for status: Accepted, Programmed
```

## Cleanup

```bash
kubectl delete -f http-route.yaml
kubectl delete -f crd.yaml
```

## Exercise
1. Explain what each of the three CRDs owns, and who would manage each in a real
   platform team.
2. Add a second `HTTPRoute` with a `/banana` path and observe routing.

## EKS note
AWS VPC Lattice + Gateway API Controller is the EKS-native way; otherwise
install the nginx Gateway Fabric on your managed nodes.
