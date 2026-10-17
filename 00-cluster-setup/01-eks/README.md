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

## Ingress
Install an ingress controller following the AWS guide:
<https://aws.amazon.com/premiumsupport/knowledge-center/eks-access-kubernetes-services/>

## Cleanup
```bash
eksctl delete cluster --region=us-east-1 --name=valaxy-eks-cluster --force
```

## Next
Continue with [01-foundations](../../01-foundations/).
