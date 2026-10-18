# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

A hands-on, example-driven Kubernetes course. Every topic lives in its own
numbered module with runnable manifests, the commands to apply them, how to
verify, and how to clean up. It is **teaching content** — clarity and
runnability matter more than feature count.

- Target platform: **AWS EKS** (notes call out where local clusters differ).
- Networking scope: **ClusterIP, NodePort, LoadBalancer, Gateway API via
  NGINX Gateway Fabric only**. Do **not** introduce Ingress resources or the
  AWS ALB/Load Balancer Controller.
- Modules deliberately excluded so far (listed as "Coming next" in
  `docs/roadmap.md`): RBAC/IRSA, NetworkPolicy, StatefulSet, PDB, VPA/Cluster
  Autoscaler, GitOps, Operators/CRDs, troubleshooting, capstone. Don't add
  them unless asked.

## Layout

```
00-cluster-setup/     EKS (01), kubeadm (02), local kind/minikube (03)
01-foundations/       namespaces, multi-resource YAML
02-pods/
03-workload-controllers/  replicaset, deployment, strategies, daemonset, jobs
04-configuration/     configmap, secret
05-storage/           emptydir, hostpath, pv-pvc-static, storageclass, csi-aws-ebs
06-networking/        backend-app, clusterip, nodeport, loadbalancer, gateway-api
07-scheduling/        nodeselector, node-affinity, taints-tolerations
08-pod-lifecycle/     probes, hooks
09-resource-management/ requests-limits, limitrange, resourcequota
10-security/          securitycontext
11-autoscaling/       hpa
12-packaging/         helm (01), kustomize (02)
13-observability/     metrics-server, monitoring, logging
docs/                 architecture.md, roadmap.md, kubectl-cheatsheet.md, good-articles.md
scripts/validate.sh   kubeconform over all plain manifests
.github/workflows/    kubesec.yml, validate.yml
```

## Conventions (enforced — do not drift)

- **Folders:** lowercase kebab-case, two-digit numeric prefix `NN-topic`,
  nested one level. No mixed casing (`Storage`, `Jobs`) or camelCase.
- **Files:** lowercase kebab-case, `.yaml` extension (never `.yml`).
- **Every module gets a `README.md`** using this exact template:
  `Objective → Prereqs → Examples → Commands → Verify → Cleanup → Exercise →
  EKS note`. Example-level READMEs inside subfolders follow the same shape.
- Cross-references between modules use relative links (`../03-workload-controllers/`).
- Each example must be independently applicable **and cleanable** — if a
  manifest depends on another (e.g. a Service on a Deployment), the README
  must say so and both must be in `Cleanup`.

## Manifest rules

- Kubernetes APIs: current versions only (`autoscaling/v2`, `networking.k8s.io/v1`,
  `batch/v1`). Never `autoscaling/v1`, never beta APIs, never PodSecurityPolicy.
- Pin image tags (`nginx:1.27.1`, `busybox:1.36`); `nginx:latest` only in the
  most basic pod example. Use `registry.k8s.io/`, not `k8s.gcr.io/`.
- Never commit binaries (`*.tar`), kubeconfigs, or credentials. The fluent-bit
  values file must use a placeholder for passwords.
- Quantity units: write memory as `Mi` (not `M`) unless deliberately teaching
  the unit trap; document the difference if so (see `02-pods/01-basic-pod/pod.yaml`).
- `06-networking` examples must keep Service selectors matched to the actual
  Pod labels — a mismatched selector is a silent 503, not a lesson.

## Before committing

1. `bash scripts/validate.sh` — kubeconform (`-strict -ignore-missing-schemas`)
   must pass with 0 invalid/0 errors. Files without `apiVersion`/`kind` (Helm
   charts, values, kustomization, eksctl config, GitHub workflows) are
   excluded by `EXCLUDES` in the script; add any new non-manifest YAML there.
2. Keep changes consistent with the numbered structure; renumber with `git mv`
   when adding/removing examples so no sequence gaps appear.

## Git

- Work on a feature branch (`feature/<feature-name>` pattern); commit
  logically and push to `origin` (no PR unless asked).
- Large restructures must use `git mv` to preserve history.
- Commit messages: imperative summary line, then a bulleted body of what and why.

## History note

The repo was restructured from a flat 26-folder layout into the numbered
modules above; the old flat layout (e.g. `Storage/`, `Jobs/`, `Ingress/`,
`HorizantalPodAutoscaler/`) should not be reintroduced. Old paths appear only
in `git log` history.
