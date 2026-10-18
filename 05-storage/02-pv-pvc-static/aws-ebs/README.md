# Static Provisioning

## Prerequisites

1. Kubernetes 1.13+ (CSI 1.0).
2. The [aws-ebs-csi-driver](https://github.com/kubernetes-sigs/aws-ebs-csi-driver) installed.
3. An existing Amazon EBS volume (created below) — the CSI driver does not
   create volumes for a static PV, it only adopts one you point it at.

## Usage

This example shows you how to create and consume a `PersistentVolume` from an
existing EBS volume with static provisioning.

1. Create a `gp3` volume. Pick an Availability Zone that has nodes in it —
   `kubectl get nodes -o custom-columns=NAME:.metadata.name,ZONE:.metadata.labels.topology\.kubernetes\.io/zone`
   — because a static PV can only attach in the zone it was created in:

    ```sh
    $ aws ec2 create-volume \
        --availability-zone us-east-1a \
        --size 5 \
        --volume-type gp3 \
        --tag-specifications 'ResourceType=volume,Tags=[{Key=Name,Value=learn-k8s-demo}]'

    {
        "VolumeId": "vol-0123456789abcdef0",
        ...
    }
    ```

2. Edit [pv.yaml](./manifests/pv.yaml) to include that `volumeHandle` and the
   matching zone. The committed manifest uses placeholder values, so it will not
    bind until you replace both:

    ```yaml
    apiVersion: v1
    kind: PersistentVolume
    metadata:
      name: test-pv
    spec:
      accessModes:
      - ReadWriteOnce
      capacity:
        storage: 5Gi
      csi:
        driver: ebs.csi.aws.com
        fsType: ext4
        volumeHandle: vol-0123456789abcdef0
      nodeAffinity:
        required:
          nodeSelectorTerms:
            - matchExpressions:
                - key: topology.ebs.csi.aws.com/zone
                  operator: In
                  values:
                    - us-east-1a
    ```

    The `nodeAffinity` block is not optional. It is what pins the PV to the
    volume's AZ, which is why this PVC often stays `Pending` if the zone is wrong.

3. Deploy the provided pod on your cluster along with the `PersistentVolume` and `PersistentVolumeClaim`:
    ```sh
    $ kubectl apply -f manifests

    persistentvolumeclaim/ebs-claim created
    pod/app created
    persistentvolume/test-pv created
    ```

4. Validate the `PersistentVolumeClaim` is bound to your `PersistentVolume`.
    ```sh
    $ kubectl get pvc ebs-claim

    NAME        STATUS   VOLUME    CAPACITY   ACCESS MODES   STORAGECLASS   AGE
    ebs-claim   Bound    test-pv   5Gi        RWO                           53s
    ```

    `STORAGECLASS` is empty on purpose: a static PV does not go through dynamic
    provisioning, so it is not tied to a StorageClass.

5. Validate the pod successfully wrote data to the statically provisioned volume:
    ```sh
    $ kubectl exec app -- cat /data/out.txt

    Tue Feb 22 20:51:37 UTC 2022
    ...
    ```

6. Cleanup resources. A statically provisioned PV is **not** deleted by
    `kubectl delete`, so delete the EBS volume yourself or you will pay for it:

    ```sh
    $ kubectl delete -f manifests

    persistentvolumeclaim "ebs-claim" deleted
    pod "app" deleted
    persistentvolume "test-pv" deleted
    $ aws ec2 delete-volume --volume-id vol-0123456789abcdef0
    ```