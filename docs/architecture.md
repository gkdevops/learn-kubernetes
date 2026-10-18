# Architecture Primer

Read this before module 02 (`pods`). It explains what the cluster actually runs
when you `kubectl apply` something.

## The API is the product

Kubernetes is a **declarative state machine**. You send a desired state
(the `spec` in YAML) to the API server; controllers continuously compare it to
the actual state (`status`) and act on any difference — that difference is the
whole game, and it is called **reconciliation**.

```
                  ┌─────────────── Control plane ────────────────┐
                  │                                              │
  kubectl ────────►  API server  ◄──── every controller watches    │
                  │    |    ◄──── kubelet reports Pod status      │
                  │    ▼                                         │
                  │    etcd  (source of truth)                   │
                  └───────────────────────────────────────────────┘
                       │              │
                       ▼              ▼
                  ┌──────── node ┐ ┌──────── node ┐
                  │ kubelet      │ │ kubelet      │
                  │ kube-proxy   │ │ kube-proxy   │
                  │ containerd   │ │ containerd   │
                  └──────────────┘ └──────────────┘
```

## Control plane

| Component | Job | What breaks without it |
|-----------|-----|------------------------|
| **API server** | The single front door. Validates every read/write, persists to etcd and notifies watchers. | Nothing works: `kubectl`, controllers and nodes all talk to it |
| **etcd** | Consistent key-value store holding all objects | No cluster state at all |
| **Scheduler** | Assigns unscheduled Pods to nodes (CPU/mem, affinity, taints) | New Pods sit in `Pending` |
| **Controller manager** | Runs the controllers: ReplicaSet, Deployment, Job, endpoints, node lifecycle, … | Objects stop converging; Pods never get replaced |
| **Cloud controller manager** (EKS) | Bridges to AWS: load balancers, node registration | `LoadBalancer` Services never get an IP |

## Nodes (workers)

| Component | Job |
|-----------|-----|
| **kubelet** | The node's agent. Watches the API server for Pods destined for this node, and starts/stops them via the container runtime. Feeds back status and runs probes. |
| **Container runtime** (containerd) | Actually pulls images and runs containers (via CRI). |
| **kube-proxy** | Implements Service `ClusterIP`/`NodePort` using iptables/IPVS. |
| **CNI plugin** | Gives each Pod an IP address and handles Pod-to-Pod networking (on EKS: AWS VPC CNI). |

## Special object kinds

Most objects ("Pod", "Deployment") are **workload objects** whose desired state
you submit. A few are **configuration** for the controllers themselves:
`PriorityClass`, `StorageClass`, `GatewayClass`, `RuntimeClass`. When you see
`Class` in a name, it is usually a way to choose *which* controller handles the
resource (it keeps Kubernetes pluggable).

## Roadmap in this repo

- **What runs where** — this page
- **What you configure** — modules 02..13, roughly following "workloads →
  configuration → state → networking → scale → operate"

## EKS note
On EKS you never manage control-plane components: AWS runs the API server, etcd,
scheduler and controllers; you only manage *nodes* (managed node groups) and
add-ons (VPC CNI, EBS CSI, CoreDNS, metrics-server). That is exactly why
`kubectl get pods -n kube-system` looks different depending on whether you use
EKS or a kubeadm cluster.
