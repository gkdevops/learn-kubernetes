# 00-cluster-setup / 02 — kubeadm (self-managed)

## Objective
Build a cluster by hand to understand the control plane: install containerd,
kubeadm, kubelet, kubectl, then initialise.

## Prerequisites
- One or more Ubuntu nodes.
- Root/sudo access.

## Install runtime + Kubernetes
Run [install_containerd.sh](install_containerd.sh) on **every** node. It:
1. Loads `overlay` and `br_netfilter` kernel modules.
2. Sets the required sysctls for Kubernetes networking.
3. Installs and configures containerd (`SystemdCgroup = true`).
4. Disables swap and installs `kubelet kubeadm kubectl`.

## Initialise the cluster
On the **control-plane** node only:

```bash
sudo kubeadm init --pod-network-cidr 192.168.0.0/16
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

Install a CNI (Calico shown):

```bash
kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/tigera-operator.yaml
curl -O https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/custom-resources.yaml
kubectl apply -f custom-resources.yaml
```

Join workers with the `kubeadm join` command printed by `kubeadm init`.

## Verify
```bash
kubectl get nodes
kubectl get pods -n kube-system
```

## Cleanup
```bash
sudo kubeadm reset
```
