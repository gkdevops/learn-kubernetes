# kubectl Cheat Sheet

## Cluster & context

```bash
kubectl version --short
kubectl cluster-info
kubectl config get-contexts
kubectl config current-context
kubectl config use-context <name>
kubectl config set-context dev --namespace=development --cluster=<cluster> --user=<user>
kubectl get nodes -o wide
```

## Namespaces

```bash
kubectl get namespaces
kubectl create namespace development
kubectl apply -f namespace.yaml
kubectl describe namespace development
kubectl delete namespace development
```

## The core verbs

```bash
kubectl apply -f <file|dir>        # create/update from manifest
kubectl create -f <file>           # create (fails if exists)
kubectl delete -f <file>
kubectl get <kind> [-o wide|-o yaml|-o json]
kubectl describe <kind> <name>     # events + details, best for debugging
kubectl edit <kind> <name>
kubectl explain <kind>.spec       # built-in API docs
```

## Pods & workloads

```bash
kubectl get pods -o wide
kubectl get pods -w                     # watch
kubectl describe pod <name>
kubectl logs <pod> [-c <container>] [-f]
kubectl exec -it <pod> -- bash
kubectl port-forward <pod> 8080:80
kubectl delete pod <name> --force --grace-period=0

kubectl get deploy,rs,pods
kubectl rollout status deployment/<name>
kubectl rollout history deployment/<name>
kubectl rollout undo deployment/<name>
kubectl scale deployment/<name> --replicas=5
kubectl set image deployment/<name> <container>=<image>
```

## Services, Gateway API, config

```bash
kubectl get svc,ep
kubectl describe svc <name>
kubectl get gatewayclass,gateway,httproute
kubectl create configmap my-config --from-file=./files --from-literal=KEY=value
kubectl get configmap <name> -o yaml
kubectl create secret generic my-secret --from-literal=password='s3cr3t'
kubectl get secret <name> -o jsonpath='{.data.password}' | base64 -d
```

## Storage

```bash
kubectl get pv,pvc,storageclass
kubectl describe pvc <name>
```

## Scheduling

```bash
kubectl label node <node> disktype=ssd
kubectl taint node <node> type=2xlarge:NoSchedule
kubectl taint node <node> type=2xlarge:NoSchedule-   # remove taint
kubectl cordon <node>
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data
kubectl uncordon <node>
```

## Scaling & metrics

```bash
kubectl top nodes
kubectl top pods
kubectl get hpa
kubectl autoscale deployment <name> --min=1 --max=10 --cpu-percent=50
```

## Debugging

```bash
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl get pod <name> -o jsonpath='{.status.containerStatuses[*].state}'
kubectl describe pod <name> | sed -n '/Events/,$p'
kubectl run tmp --image=busybox -it --rm -- sh
```

## Output & templating

```bash
kubectl get pods -o custom-columns=NAME:.metadata.name,STATUS:.status.phase
kubectl get pods -o jsonpath='{.items[*].metadata.name}'
kubectl get deploy <name> -o yaml > manifest.yaml
kubectl diff -f manifest.yaml
```
