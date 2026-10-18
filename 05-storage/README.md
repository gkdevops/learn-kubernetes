# 05 — Storage

## Objective
Understand the Kubernetes storage model: ephemeral volumes, static PV/PVC
binding, dynamic provisioning with StorageClasses, and CSI drivers on EKS.

## Prereqs
[02-pods](../02-pods/).

## Examples
| Folder | What it shows |
|--------|---------------|
| [01-emptydir](01-emptydir/) | Ephemeral scratch space, shared between containers |
| [02-hostpath](02-hostpath/) | Bind-mount a node path (learning only) |
| [03-pv-pvc-static](03-pv-pvc-static/) | Manual PersistentVolume + PVC binding (local & AWS EBS) |
| [04-storageclass-dynamic](04-storageclass-dynamic/) | PVC auto-provisioned by a StorageClass (EBS CSI) |
| [05-csi-aws-ebs](05-csi-aws-ebs/) | Installing the AWS EBS CSI driver |

## Commands
```bash
kubectl apply -f 01-emptydir/empty-dir.yaml
kubectl apply -f 02-hostpath/hostpath.yaml

kubectl apply -f 03-pv-pvc-static/local/
kubectl get pv,pvc

kubectl apply -f 04-storageclass-dynamic/manifests/
kubectl get pvc ebs-claim
```

## Verify
`kubectl get pvc` shows `Bound`. For the dynamic example, exec into the Pod and
`cat /data/out.txt` to see data written to the volume.

## Cleanup
```bash
kubectl delete -f 01-emptydir/ -f 02-hostpath/
kubectl delete -f 03-pv-pvc-static/local/
kubectl delete -f 04-storageclass-dynamic/manifests/
```

## Exercise
1. Create a PVC, mount it into two Pods with `ReadWriteOnce` — what happens?
2. Explain why `emptyDir` data disappears when the Pod is deleted.

## EKS note
- Use the `ebs.csi.aws.com` StorageClass with `gp3` for cost/performance.
- EBS is `ReadWriteOnce` and **Availability Zone bound**; EFS is `ReadWriteMany`.
