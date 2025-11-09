# Agentic CockroachDB Orchestrator for OpenShift (s390x)

## Overview

This repository hosts an **Agentic AI system** that autonomously **plans, deploys, tunes, and validates** a distributed database workload — **CockroachDB v24.x** — on **OpenShift (LinuxONE / s390x)**.

The system integrates six collaborating agents within a closed feedback loop — **Planner Agent**, **Operator Agent**, **Database Cluster Agent**, **Monitoring Agent**, **Feedback & Tuning Agent**, and **Human-in-the-Loop (HITL)** — working together to achieve and sustain:

- **≥ 10 000 transactions per second (TPS)**  
- **≤ 5 ms latency**

All components run purely on software-defined infrastructure (no hardware acceleration) to demonstrate a self-optimizing, explainable AI-driven DevOps workflow.

---

## 1 Objective

Design an **autonomous, closed-loop AI system** that can:

- Deploy and manage CockroachDB clusters on OpenShift  
- Monitor live performance metrics (TPS and latency)  
- Dynamically scale and tune until SLA targets are achieved  
- Validate stability through continuous feedback and human oversight  

This project illustrates an **AI-driven orchestration framework** for intelligent, policy-aware management of stateful workloads.

---

## 2 System Architecture

```
+--------------------------------------------------------------+
|           Agentic CockroachDB Orchestrator                   |
+--------------------------------------------------------------+
|  Planner Agent                                               |
|  • Evaluates SLA goals and defines the tuning plan           |
|  • Implements reasoning logic (rule-based)                   |
|  • Integrated into orchestrator_agentic.py                   |
|  • Generates next action: scale_up / optimize / hold         |
+--------------------------------------------------------------+
|  Operator Agent                                              |
|  • Deploys CockroachDB Operator CRDs and controller          |
|  • Image: quay.io/tonyfieit75/cockroach-operator:s390x-v2.10.0|
|  • Manages lifecycle of CockroachDBCluster resources         |
+--------------------------------------------------------------+
|  Database Cluster Agent                                      |
|  • Provisions and configures CockroachDB nodes               |
|  • Handles CPU/memory/storage and replication settings       |
|  • Image: quay.io/tonyfieit75/cockroachdb-s390x:23.1.2       |
|  • Uses OpenShift StorageClass (managed-nvme)                |
+--------------------------------------------------------------+
|  Monitoring Agent                                            |
|  • Deploys Prometheus and Grafana                            |
|  • Collects and visualizes performance metrics               |
|  • Publishes metrics to Feedback Agent via PromQL endpoints  |
+--------------------------------------------------------------+
|  Feedback & Tuning Agent                                     |
|  • Implements benchmark + metrics collection loop            |
|  • Evaluates SLA compliance (≥10 K TPS / ≤ 5 ms)             |
|  • Applies configuration patches via Operator API            |
|  • File: orchestrator_agentic.py                             |
+--------------------------------------------------------------+
|  Human-in-the-Loop (HITL)                                   |
|  • Requests approval for planner decisions (scale/optimize) |
|  • CLI-based interaction (future: Slack/WhatsApp integration)|
|  • Ensures transparency and safety                          |
+--------------------------------------------------------------+
```

---

## 3 Repository Structure

```
agentic-cockroachdb/
├── Chart.yaml
├── values.yaml
├── orchestrator_agentic.py      # updated with Planner + HITL agents
├── ci/
│   ├── deploy_agentic_cockroachdb.sh
│   └── uninstall_agentic_cockroachdb.sh
├── templates/
│   ├── cockroachdb-cluster.yaml
│   ├── deployment-operator.yaml
│   ├── deployment-agents.yaml
│   ├── configmap-agents.yaml
│   ├── prometheus.yaml
│   ├── grafana.yaml
│   ├── rbac.yaml
│   ├── serviceaccount.yaml
│   └── namespace.yaml
└── README.md
```

---

## 4 Agent Roles and Interactions

| Agent | Description |
|--------|--------------|
| **Planner Agent** | Embedded inside `orchestrator_agentic.py`. Evaluates metrics and proposes the next step (scale_up / optimize / hold). |
| **Operator Agent** | Installs CockroachDB Operator CRDs and controls the cluster lifecycle. |
| **Database Cluster Agent** | Configures CockroachDB nodes and resources through the Operator CR. |
| **Monitoring Agent** | Deploys Prometheus/Grafana and collects TPS & latency metrics. |
| **Feedback & Tuning Agent** | Executes the benchmark–metric–patch loop to reach SLA. |
| **Human-in-the-Loop (HITL)** | Approves planner actions interactively; provides governance. |

---

## 5 Configuration (`values.yaml`)

```yaml
namespace: agentic-db

cockroachdb:
  nodes: 5
  storageClass: managed-nvme
  storage: 1Ti
  cpu: 8
  memory: 32Gi
  image: quay.io/tonyfieit75/cockroachdb-s390x:23.1.2

agents:
  image: quay.io/tonyfieit75/agentic-orchestrator:s390x-latest
  replicas: 1
  feedbackInterval: 30m
  prometheusEndpoint: http://prometheus:9090
  grafanaEndpoint: http://grafana:3000
  targetSLA:
    tps: 10000
    latency_ms: 5

monitoring:
  enabled: true
  storageClass: managed-nvme
  prometheusStorage: 50Gi
  grafanaStorage: 20Gi
```

---

## 6 Deployment Procedure

### Prerequisites
- OpenShift cluster with `oc`, `helm`, and `yq`
- Logged-in cluster session (`oc whoami`)
- StorageClass `managed-nvme`
- Access to quay.io images

### Deploy
```bash
./ci/deploy_agentic_cockroachdb.sh
```

This script will:
1. Create namespace `agentic-db`
2. Deploy Operator Agent
3. Deploy Database Cluster Agent
4. Deploy Monitoring stack
5. Deploy Feedback & Planner Orchestrator Agent
6. Wait for all components to be ready

### Verify
```bash
oc get pods -n agentic-db
```

---

## 7 Feedback–Planner–Human Loop

The **orchestrator_agentic.py** script now forms a fully functional closed feedback loop:

1. **Benchmark** – Launches a TPCC test job.  
2. **Feedback** – Collects TPS and latency metrics from Prometheus.  
3. **Planner** – Decides whether to scale or optimize.  
4. **HITL** – Requests human approval for the proposed change.  
5. **Execution** – Applies change using OpenShift `oc patch`.  
6. **Re-evaluate** – Repeats until SLA (10 K TPS / 5 ms) is met.

### Example Console Flow
```
📊 Current TPS = 9780.25, P99 Latency = 6.1 ms
🧠 Planner Decision: TPS below target (9780.25 < 10000), planning to add nodes.
Approve action 'scale_up'? (y/n): y
🔧 Scaling CockroachDB nodes: 5 → 6
✅ Benchmark job submitted.
```

---

## 8 Human-in-the-Loop Interaction

Currently the **HITL Agent** operates via CLI input (`y/n`). In future releases this will be extended to:
- Slack or Telegram Webhooks
- Twilio WhatsApp messages for remote approvals
- Policy-based auto-approval based on thresholds

This ensures safety and explainability — humans supervise, AI automates.

---

## 9 Example Test Results

| Metric | Target | Result | Status |
|---------|---------|---------|---------|
| TPS | ≥ 10 000 | 10 320 | Pass |
| Latency | ≤ 5 ms | 4.8 ms | Pass |
| Cluster Size | 5 nodes | 5 nodes | Pass |
| SLA Stability | 30 min | Stable | Pass |

---

## 10 Uninstallation

Clean removal:

```bash
./ci/uninstall_agentic_cockroachdb.sh
```

Performs:
- Helm release removal  
- CRD and PVC cleanup  
- Namespace (optional)  
- Final verification of remaining resources  

---

## 11 Future Enhancements

- Replace rule-based planner with LLM-driven Planner Agent (WatsonX.ai or LangChain)  
- Integrate Slack/Twilio for HITL confirmation  
- Add predictive scaling based on metric trends  
- Extend to CockroachDB v25+ and Postgres variants  
- Introduce policy-based reinforcement learning for tuning  

---

## 12 Author

**Antoine Fievre**  
IBM LinuxONE Solution Architect  
Focus : AI-Driven Automation, Database Optimization, and Intelligent Orchestration on s390x

---

## 13 License

Released under the **Apache 2.0 License**.  
See [LICENSE](LICENSE) for details.


