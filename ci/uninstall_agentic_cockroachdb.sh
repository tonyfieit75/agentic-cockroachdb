#!/bin/bash
# ============================================================
#  Agentic CockroachDB Full Cleanup Script (s390x Edition)
# ============================================================
# Author: Antoine Fievre
# Platform: OpenShift (LinuxONE / s390x)
# Version: 1.2 - CI/CD Safe (Idempotent)
# ============================================================

set -e

CHART_NAME="agentic-cockroachdb"
NAMESPACE=$(yq '.namespace' values.yaml)

echo "🧹 Starting Cleanup for Agentic CockroachDB Environment"
echo "------------------------------------------------------"
echo "Namespace: $NAMESPACE"
echo "Chart Release: $CHART_NAME"
echo "------------------------------------------------------"

# ---------------------------
# Step 1: Check Prerequisites
# ---------------------------
for cmd in oc helm yq; do
  if ! command -v $cmd &>/dev/null; then
    echo "❌ Error: '$cmd' command not found in PATH. Please install it before running cleanup."
    exit 1
  fi
done

# ---------------------------
# Step 2: Check Namespace
# ---------------------------
if ! oc get namespace "$NAMESPACE" >/dev/null 2>&1; then
  echo "⚠️ Namespace '$NAMESPACE' does not exist. Nothing to clean up."
  exit 0
fi

echo "✅ Namespace '$NAMESPACE' found."

# ---------------------------
# Step 3: Detect Helm Release
# ---------------------------
if helm status "$CHART_NAME" -n "$NAMESPACE" >/dev/null 2>&1; then
  echo "🧠 Helm release '$CHART_NAME' found — uninstalling..."
  helm uninstall "$CHART_NAME" -n "$NAMESPACE"
else
  echo "ℹ️ No Helm release named '$CHART_NAME' found in namespace '$NAMESPACE'."
fi

# ---------------------------
# Step 4: Delete Custom Resources & Manual Deployments
# ---------------------------
echo "🧾 Cleaning up remaining Kubernetes objects..."
for file in \
  templates/configmap-agents.yaml \
  templates/deployment-agents.yaml \
  templates/deployment-operator.yaml \
  templates/prometheus.yaml \
  templates/grafana.yaml \
  templates/rbac.yaml \
  templates/serviceaccount.yaml; do

  if [[ -f "$file" ]]; then
    echo "🗑️ Deleting $file ..."
    oc delete -f "$file" -n "$NAMESPACE" --ignore-not-found
  fi
done

# ---------------------------
# Step 5: Delete CockroachDB CRDs (if installed by operator)
# ---------------------------
echo "🧱 Checking for CockroachDB CRDs..."
CRD_LIST=$(oc get crd | grep -E "cockroach|crdb" | awk '{print $1}' || true)
if [ -n "$CRD_LIST" ]; then
  echo "🗑️ Deleting CRDs related to CockroachDB:"
  echo "$CRD_LIST"
  echo "$CRD_LIST" | xargs -I {} oc delete crd {} --ignore-not-found || true
else
  echo "✅ No CockroachDB CRDs detected."
fi

# ---------------------------
# Step 6: Delete PVCs (DB + Monitoring)
# ---------------------------
echo "🧱 Deleting Persistent Volume Claims..."
PVC_LIST=$(oc get pvc -n "$NAMESPACE" --no-headers -o custom-columns=":metadata.name" || true)
if [ -n "$PVC_LIST" ]; then
  echo "$PVC_LIST" | while read -r pvc; do
    echo "🗑️ Deleting PVC: $pvc"
    oc delete pvc "$pvc" -n "$NAMESPACE" --ignore-not-found
  done
else
  echo "✅ No PVCs found."
fi

# ---------------------------
# Step 7: Delete Remaining Pods or Jobs
# ---------------------------
echo "🧽 Deleting any leftover pods or jobs..."
oc delete pods --all -n "$NAMESPACE" --ignore-not-found
oc delete jobs --all -n "$NAMESPACE" --ignore-not-found

# ---------------------------
# Step 8: Optionally Delete Namespace
# ---------------------------
if [[ -t 0 ]]; then
  # interactive mode
  read -p "⚠️ Do you want to delete the entire namespace '$NAMESPACE'? (y/N): " confirm
  if [[ "$confirm" =~ ^[Yy]$ ]]; then
    echo "💥 Deleting namespace $NAMESPACE ..."
    oc delete namespace "$NAMESPACE" --ignore-not-found
  else
    echo "🛑 Namespace retained. Cleanup complete within $NAMESPACE."
  fi
else
  # non-interactive (CI/CD mode)
  echo "🧠 CI/CD mode detected — retaining namespace for logs."
fi

# ---------------------------
# Step 9: Verification
# ---------------------------
echo "🔍 Final Verification..."
sleep 5

if oc get ns "$NAMESPACE" >/dev/null 2>&1; then
  echo "🗂️ Namespace '$NAMESPACE' still exists. Remaining resources:"
  oc get all -n "$NAMESPACE" || true
else
  echo "✅ Namespace '$NAMESPACE' fully removed."
fi

echo "------------------------------------------------------"
echo "🧹 Cleanup Complete!"
echo "All Agentic CockroachDB components have been safely removed."
echo "------------------------------------------------------"

