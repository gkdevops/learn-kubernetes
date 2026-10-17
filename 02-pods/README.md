# 02 — Pods

## Objective
A Pod is the smallest deployable unit in Kubernetes. Learn its anatomy: the four
YAML sections (apiVersion, kind, metadata, spec).

## Prereqs
A working cluster and `kubectl`.

## Examples
| File | What it shows |
|------|---------------|
| [01-basic-pod/pod.yaml](01-basic-pod/pod.yaml) | A single nginx container with resource limits |

## Commands
```bash
kubectl apply -f 01-basic-pod/pod.yaml
kubectl get pods -o wide
kubectl describe pod sample-pod
kubectl exec -it sample-pod -- bash
```

## Verify
The Pod reaches `Running`. Inside the container, `hostname` and `cat /etc/hosts`
show the Pod's identity.

## Cleanup
```bash
kubectl delete -f 01-basic-pod/pod.yaml
```

## Exercise
2. Pin the image tag (replace `nginx:latest` with something like `nginx:1.27.1`)
   and re-apply — what does `kubectl apply` do?
2. Delete the Pod. How is it recreated? (It is not — Pods are not self-healing.
   That is the job of a ReplicaSet → see [03-workload-controllers](../03-workload-controllers/).)

## EKS note
Pods inherit networking from the VPC CNI — each Pod gets a real VPC IP address.
