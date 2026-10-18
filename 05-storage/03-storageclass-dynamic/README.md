# Dynamic Volume Provisioning

## Prerequisites

1. Kubernetes 1.13+ (CSI 1.0).
2. The [aws-ebs-csi-driver](https://github.com/kubernetes-sigs/aws-ebs-csi-driver) installed.

## Usage

This example shows you how to dynamically provision an EBS volume in your cluster.

The `ebs-sc` StorageClass provisions **`gp3`** volumes (encrypted, expandable,
`reclaimPolicy: Delete`). Three of those settings matter on EKS:

- `parameters.type: gp3` - without it the driver falls back to its `gp2` default.
- `volumeBindingMode: WaitForFirstConsumer` - provisioning waits for a Pod, so
  the scheduler chooses the node first and the disk is created in that node's AZ.
  With `Immediate` the disk could land in an AZ your Pods cannot use, and the PVC
  would sit `Pending` forever.
- `allowVolumeExpansion: true` - lets the PVC grow in place later.

1. Deploy the provided pod on your cluster along with the `StorageClass` and `PersistentVolumeClaim`:
    ```sh
    $ kubectl apply -f manifests

    persistentvolumeclaim/ebs-claim-dynamic created
    pod/app created
    storageclass.storage.k8s.io/ebs-sc created
    ```

2. Validate the `PersistentVolumeClaim` is bound to your `PersistentVolume`.
    ```sh
    $ kubectl get pvc ebs-claim-dynamic

    NAME        STATUS   VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS   AGE
    ebs-claim-dynamic   Bound   pvc-9124c6d0-382a-49c5-9494-bcb60f6c0c9c   4Gi        RWO   ebs-sc   30m
    ```

3. Validate the pod successfully wrote data to the dynamically provisioned volume:
    ```sh
    $ kubectl exec app-dynamic -- cat /data/out.txt

    Tue Feb 22 01:24:44 UTC 2022
    ...
    ```

4. Cleanup resources:
    ```sh
    $ kubectl delete -f manifests

    persistentvolumeclaim "ebs-claim-dynamic" deleted
    pod "app-dynamic" deleted
    storageclass.storage.k8s.io "ebs-sc" deleted
    ```
