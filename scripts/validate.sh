#!/usr/bin/env bash
#
# Validate all plain Kubernetes manifests in this repo with kubeconform.
#
# Usage:  bash scripts/validate.sh
set -euo pipefail

if ! command -v kubeconform >/dev/null 2>&1; then
  echo "kubeconform not found. Install it from https://github.com/yannh/kubeconform" >&2
  exit 1
fi

EXCLUDES='\.git/|\.github/|12-packaging/01-helm|12-packaging/02-kustomize|00-cluster-setup/01-eks/cluster\.yaml|13-observability/03-logging/fluentbit-values\.yaml|values\.yaml$'

mapfile -t files < <(
  find . -path ./.git -prune -o -type f \( -name '*.yaml' -o -name '*.yml' \) -print \
    | grep -Ev "$EXCLUDES" \
    | sort
)

echo "Validating ${#files[@]} manifest files..."
kubeconform -strict -ignore-missing-schemas -summary "${files[@]}"
