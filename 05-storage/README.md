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
| [02-pv-pvc-static](02-pv-pvc-static/) | Manual PersistentVolume + PVC binding (local & AWS EBS) |
| [03-storageclass-dynamic](03-storageclass-dynamic/) | PVC auto-provisioned by a StorageClass (EBS CSI, `gp3`) |
| [04-csi-aws-ebs](04-csi-aws-ebs/) | Installing the AWS EBS CSI driver |

> **`hostPath` is deliberately not covered here.** It grants a container access
> to a directory on the node, which breaks Pod isolation, ties the workload to one
> node, and exposes the host filesystem to anything that can create a Pod in the
> namespace. Every time you see it in the wild it is a migration waiting to
> happen. Use a CSI driver (EBS, EFS) or a cloud-native volume instead.

## Commands
```bash
kubectl apply -f 01-emptydir/empty-dir.yaml

kubectl apply -f 02-pv-pvc-static/local/
kubectl get pv,pvc

kubectl apply -f 03-storageclass-dynamic/manifests/
kubectl get pvc ebs-claim
```

## Verify
`kubectl get pvc` shows `Bound`. For the dynamic example, exec into the Pod and
`cat /data/out.txt` to see data written to the volume.

## Cleanup
```bash
kubectl delete -f 01-emptydir/
kubectl delete -f 02-pv-pvc-static/local/
kubectl delete -f 03-storageclass-dynamic/manifests/
```

## Exercise
1. Create a PVC, mount it into two Pods with `ReadWriteOnce` — what happens?
2. Explain why `emptyDir` data disappears when the Pod is deleted.
3. Expand the dynamic PVC (`kubectl patch pvc ebs-claim -p '{"spec":{"resources":{"requests":{"storage":"8Gi"}}}}'`)
   and watch the volume grow in place — this only works because the StorageClass
   sets `allowVolumeExpansion: true`.

## EKS note
- Use the `ebs.csi.aws.com` StorageClass with `gp3` for cost/performance. `gp3`
  is cheaper per GB than `gp2` and defaults to 3000 IOPS / 125 MB/s, which beats
  `gp2`'s baseline; burst credits are a `gp2` concept and do not apply.
- EBS is `ReadWriteOnce` and **Availability Zone bound**; EFS is `ReadWriteMany`.
- The cluster also ships a default StorageClass named `gp2` (EBS, `gp2` type).
  Prefer the `gp3` StorageClass from [03-storageclass-dynamic](03-storageclass-dynamic/)
  so the course is consistent about volume type.