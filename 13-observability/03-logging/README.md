# Logging (ELK / Fluent Bit)

## Objective
Ship Pod logs to Elasticsearch so you can search them in Kibana.

## Prerequisites
- An EKS cluster (see [00-cluster-setup](../../00-cluster-setup/)).
- `helm` and `kubectl` configured.

## 1. (EKS) create the EBS CSI IRSA role
Elasticsearch needs a persistent volume, so first give the EBS CSI driver IAM
permissions via IRSA:

```bash
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster valaxy-eks-cluster \
  --role-name AmazonEKS_EBS_CSI_DriverRole \
  --role-only \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve

ARN=$(aws iam get-role --role-name AmazonEKS_EBS_CSI_DriverRole --query 'Role.Arn' --output text)
eksctl create addon --cluster valaxy-eks-cluster --name aws-ebs-csi-driver --version latest --service-account-role-arn $ARN --force
```

## 2. Create the namespace and install Elasticsearch
```bash
kubectl create namespace logging

helm repo add elastic https://helm.elastic.co
helm repo update

helm install elasticsearch \
  --set replicas=1 \
  --set volumeClaimTemplate.storageClassName=gp2 \
  -n logging elastic/elasticsearch
```

Read the generated credentials:

```bash
kubectl get secret --namespace=logging elasticsearch-master-credentials \
  -o jsonpath='{.data.username}' | base64 -d
kubectl get secret --namespace=logging elasticsearch-master-credentials \
  -o jsonpath='{.data.password}' | base64 -d
```

## 3. Install Kibana
```bash
helm install kibana --set service.type=LoadBalancer elastic/kibana -n logging
```

## 4. Install Fluent Bit
`fluentbit-values.yaml` (in this folder) tails container logs and ships them to
Elasticsearch. Set the Elasticsearch password there (via a Secret/env var —
never commit it) before installing:

```bash
helm repo add fluent https://fluent.github.io/helm-charts
helm install fluent-bit fluent/fluent-bit -f fluentbit-values.yaml -n logging
```

## Verify
```bash
kubectl get pods -n logging
kubectl get svc -n logging kibana-kibana    # opens Kibana on the external IP
```

## Cleanup
```bash
helm uninstall fluent-bit kibana elasticsearch -n logging
kubectl delete namespace logging
```
