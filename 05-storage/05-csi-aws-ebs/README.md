# 05-storage / 05 — AWS EBS CSI Driver

## Objective
Install `aws-ebs-csi-driver` so the cluster can provision EBS volumes via the
CSI standard. Everything in `04-storageclass-dynamic/` depends on it.

## Prerequisites
- An EKS cluster (EKS 1.20+) — the driver needs IAM permissions to manage EBS.
- `helm`.

## Option A — EKS managed add-on (recommended)
The driver IAM role already exists if you created the cluster with
[00-cluster-setup/01-eks/](../../00-cluster-setup/01-eks/). If not, create it:

```bash
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster <cluster-name> \
  --role-name AmazonEKS_EBS_CSI_DriverRole \
  --role-only \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve

ARN=$(aws iam get-role --role-name AmazonEKS_EBS_CSI_DriverRole --query 'Role.Arn' --output text)
eksctl create addon --cluster <cluster-name> --name aws-ebs-csi-driver \
  --version latest --service-account-role-arn $ARN --force
```

## Option B — Helm
```bash
helm repo add aws-ebs-csi-driver https://kubernetes-sigs.github.io/aws-ebs-csi-driver
helm repo update
helm upgrade --install aws-ebs-csi-driver aws-ebs-csi-driver/aws-ebs-csi-driver \
  --namespace kube-system
```

## Verify
```bash
kubectl get pods -n kube-system -l app.kubernetes.io/name=aws-ebs-csi-driver
```
Then apply [04-storageclass-dynamic/](../04-storageclass-dynamic/) and confirm
the PVC becomes `Bound`.

## Cleanup
```bash
helm uninstall aws-ebs-csi-driver --namespace kube-system
# or eksctl delete addon --cluster <name> --name aws-ebs-csi-driver
```

## Notes
- For encrypted volumes add the `kms:Decrypt/CreateGrant` statements to the IAM
  policy (see the upstream `example-iam-policy.json`).
- Full upstream documentation: <https://github.com/kubernetes-sigs/aws-ebs-csi-driver>.
- Assumes self-managed clusters set `--allow-privileged=true` on kube-apiserver.
- Volume snapshots need the snapshotter CRDs installed first (see
  [external-snapshotter](https://github.com/kubernetes-csi/external-snapshotter#usage)).
