#!/bin/bash
# ============================================================
#  Agentic CockroachDB Full Deployment Script (s390x Edition)
# ============================================================
# Author: Antoine Fievre
# Platform: OpenShift (LinuxONE / s390x)
# Version: 1.1

set -e

CHART_NAME="agentic-cockroachdb"
NAMESPACE=$(yq '.namespace' values.yaml)
OPERATOR_IMAGE=$(yq '.operator.image.repository' values.yaml):$(yq '.operator.image.tag' values.yaml)
COCKROACH_IMAGE=$(yq '.cockroachdb.image' values.yaml)
ORCHESTRATOR_IMAGE=$(yq '.agents.image' values.yaml)

echo "🚀 Starting Agentic CockroachDB Deployment"
echo "------------------------------------------"
echo "Namespace: $NAMESPACE"
echo "Operator Image: $OPERATOR_IMAGE"
echo "CockroachDB Image: $COCKROACH_IMAGE"
echo "Orchestrator Image: $ORCHESTRATOR_IMAGE"
echo "------------------------------------------"

# ---------------------------
# Step 1: Namespace Setup
# ---------------------------
echo "📦 Creating namespace (if not exists)..."
if ! oc get namespace "$NAMESPACE" >/dev/null 2>&1; then
  oc create namespace "$NAMESPACE"
fi

# ---------------------------
# Step 2: RBAC + ServiceAccount
# ---------------------------
echo "🔐 Applying RBAC and ServiceAccount..."
oc apply -f templates/serviceaccount.yaml -n "$NAMESPACE"
oc apply -f templates/rbac.yaml -n "$NAMESPACE"

# ---------------------------
# Step 3: Deploy Full Stack (Operator + DB + Orchestrator + Monitoring)
# ---------------------------
echo "🧠 Deploying full Agentic CockroachDB stack via Helm..."
helm upgrade --install "$CHART_NAME" . -n "$NAMESPACE" -f values.yaml --create-namespace

echo "⏳ Waiting for Cockroach Operator to be ready..."
oc rollout status deploy/cockroach-operator -n "$NAMESPACE" --timeout=180s || true

# ---------------------------
# Step 4: Wait for CockroachDB Cluster
# ---------------------------
echo "💾 Waiting for CockroachDB cluster pods..."
oc wait --for=condition=Ready pod -l app.kubernetes.io/component=cockroachdb -n "$NAMESPACE" --timeout=600s || true

# ---------------------------
# Step 5: Deploy Agentic Orchestrator Components
# ---------------------------
echo "🤖 Applying Agentic Orchestrator config..."
oc apply -f templates/configmap-agents.yaml -n "$NAMESPACE"
oc apply -f templates/deployment-agents.yaml -n "$NAMESPACE"

# ---------------------------
# Step 6: Deploy Monitoring (Prometheus + Grafana)
# ---------------------------
if [[ $(yq '.monitoring.enabled' values.yaml) == "true" ]]; then
  echo "📈 Deploying Prometheus and Grafana..."
  oc apply -f templates/prometheus.yaml -n "$NAMESPACE"
  oc apply -f templates/grafana.yaml -n "$NAMESPACE"
else
  echo "📊 Monitoring disabled in values.yaml"
fi

# ---------------------------
# Step 7: Verification
# ---------------------------
echo "🔍 Verifying deployed components..."
echo "------------------------------------------"
oc get pods -n "$NAMESPACE"
echo "------------------------------------------"
echo "✅ Deployment Complete!"
echo "🧠 Operator Image: ${OPERATOR_IMAGE}"
echo "💾 CockroachDB Image: ${COCKROACH_IMAGE}"
echo "🤖 Orchestrator Image: ${ORCHESTRATOR_IMAGE}"
echo "------------------------------------------"
echo "To view logs:"
echo "  oc logs deploy/cockroach-operator -n ${NAMESPACE} | head -20"
echo "------------------------------------------"

