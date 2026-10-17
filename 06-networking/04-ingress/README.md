# Ingress

## Objective
Route external HTTP traffic to in-cluster Services by host and path.

## Prerequisites
1. An ingress controller. Install the nginx Ingress controller:

   ```bash
   helm upgrade --install ingress-nginx ingress-nginx \
     --repo https://kubernetes.github.io/ingress-nginx \
     --namespace ingress-nginx --create-namespace

   kubectl --namespace ingress-nginx get svc ingress-nginx-controller
   ```

   On EKS, the **AWS Load Balancer Controller** is the alternative
   (`ingressClassName: alb`) — install it once, then reference it here.

## Deploy the sample apps

```bash
kubectl apply -f app.yaml        # apple + banana Pods and Services
kubectl apply -f ingress.yaml    # routes /apple and /banana
kubectl get ingress
```

## Verify
Point `mywebsite.com` at the ingress controller's address (or use
`curl -H "Host: mywebsite.com" http://<controller-ip>/apple`).

## Cleanup
```bash
kubectl delete -f ingress.yaml -f app.yaml
```
