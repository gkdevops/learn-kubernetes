#----Containerd Installation----------

#Load Kernel modules at system startup
cat <<EOF | sudo tee /etc/modules-load.d/containerd.conf
overlay
br_netfilter
EOF

# These normally reflect post server restart
# To reflect them immediately withour restarting the server
sudo modprobe overlay
sudo modprobe br_netfilter

# Now set the kernel properties for the Kubernetes networking
cat <<EOF | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf
net.bridge.bridge-nf-call-iptables = 1
net.ipv4.ip_forward = 1
net.bridge.bridge-nf-call-ip6tables = 1
EOF

# Now to Apply these properties without reboot the system
sudo sysctl --system
sudo systemctl restart systemd-modules-load.service

# Install pre-requisites
sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Install containerd
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y containerd.io

# Create default configuration file for containerd:
sudo mkdir -p /etc/containerd

# Generate default containerd configuration and save to the newly created default file:
sudo containerd config default | sudo tee /etc/containerd/config.toml

sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# Restart containerd to ensure new configuration file usage:
sudo systemctl enable containerd
sudo systemctl restart containerd

#--------------------------------------------
# Install Kubernetes

# Disable swap:
sudo swapoff -a

# Install dependency packages:
sudo apt-get update && sudo apt-get install -y apt-transport-https curl

#Download and add GPG key:
# curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo apt-key add -
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.31/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

# Add Kubernetes to repository list:
echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.31/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list

# Update package listings:
sudo apt-get update

# Install Kubernetes packages (Note: If you get a dpkg lock message, just wait a minute or two before trying the command again):
sudo apt-get install -y kubelet kubeadm kubectl

# Turn off automatic updates:
sudo apt-mark hold kubelet kubeadm kubectl

# Initialize the Cluster
# Initialize the Kubernetes cluster on the control plane node using kubeadm (Note: This is only performed on the Control Plane Node):
#kubeadm init --pod-network-cidr 192.168.0.0/16

# Install the Calico Network Add-On
# Only the control plane node, install Calico Networking:
#kubectl create -f https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/tigera-operator.yaml
#curl https://raw.githubusercontent.com/projectcalico/calico/v3.26.1/manifests/custom-resources.yaml -O
#kubectl create -f custom-resources.yaml
