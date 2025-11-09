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
|  • Reads SLA objectives (TPS / latency)                      |
|  • Generates deployment and tuning plan                      |
|  • Coordinates actions among all other agents                |
|  • Can employ AI reasoning or rule-based logic               |
+--------------------------------------------------------------+
|  Operator Agent                                              |
|  • Deploys CockroachDB Operator CRDs and controller          |
|  • Image: quay.io/tonyfieit75/cockroach-operator:s390x-v2.10.0 |
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
|  • Executes Planner’s instructions (orchestrator.py)         |
|  • Queries Prometheus for TPS and latency                    |
|  • Evaluates SLA compliance (≥10 K TPS / ≤ 5 ms)             |
|  • Applies configuration patches via Operator API            |
+--------------------------------------------------------------+
|  Human-in-the-Loop (HITL)                                    |
|  • Reviews dashboards and system decisions                   |
|  • Approves major actions or policy changes                  |
|  • Ensures transparency and governance                       |
+--------------------------------------------------------------+
```

---

## 3 Repository Structure

```
agentic-cockroachdb/
├── Chart.yaml
├── values.yaml
├── orchestrator.py
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
| **Planner Agent** | Defines desired SLA goals and formulates deployment + tuning plan; may use ML/LLM reasoning in future versions. |
| **Operator Agent** | Installs CockroachDB Operator CRDs and controls the cluster lifecycle. |
| **Database Cluster Agent** | Configures CockroachDB nodes and resources through the Operator CR. |
| **Monitoring Agent** | Deploys Prometheus/Grafana and collects TPS & latency metrics. |
| **Feedback & Tuning Agent** | Executes the control loop to reach SLA; scales and revalidates performance. |
| **Human-in-the-Loop (HITL)** | Observes results via Grafana or CLI; approves tuning or termination of loops. |

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
- Access to images on quay.io/tonyfieit75

### Deploy
```bash
./ci/deploy_agentic_cockroachdb.sh
```

This script will:
1. Create namespace `agentic-db`
2. Deploy Operator Agent
3. Deploy Database Cluster Agent
4. Deploy Monitoring stack
5. Deploy Feedback & Tuning Agent
6. Wait for all components to be ready

### Verify
```bash
oc get pods -n agentic-db
```

---

## 7 Feedback Control Loop

The **Feedback & Tuning Agent** executes the logic in `orchestrator.py`:

1. Run TPC-C benchmark  
2. Query Prometheus:
   ```promql
   rate(sql_exec_count[1m])
   histogram_quantile(0.99, rate(sql_exec_latency_bucket[1m]))
   ```
3. Evaluate SLA targets  
4. If SLA not met, scale cluster:
   ```bash
   oc patch crdbcluster crdb-prod --type=merge -p '{"spec":{"nodes":5}}'
   ```
5. Loop until performance stabilizes.

---

## 8 Planner–Human Collaboration Loop

The **Planner Agent** periodically reports its plan and reasoning steps to the **Human-in-the-Loop**, enabling transparency and control.

| Phase | Actor | Action |
|--------|--------|---------|
| Define | Planner Agent | Reads goal (10 K TPS / 5 ms) and creates deployment plan. |
| Execute | Feedback & Tuning Agent | Applies plan and collects results. |
| Observe | Monitoring Agent | Reports metrics to Planner and HITL. |
| Validate | Human-in-the-Loop | Reviews Grafana dashboards and approves final SLA. |
| Learn | Planner Agent | Updates future plans based on historical results. |

This design maintains **autonomy with oversight**, ensuring safe and explainable operation.

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

- Add AI/LLM-driven Planner Agent (WatsonX.ai or LangChain)  
- Integrate GitOps and policy reconciliation  
- Extend to CockroachDB v25+ and Postgres variants  
- Implement OpenTelemetry for full traceability  
- Add cost-based scaling and energy efficiency metrics  

---

## 12 Author

**Antoine Fievre**  
IBM LinuxONE Solution Architect  
Focus : AI-Driven Automation, Database Optimization, and Intelligent Orchestration on s390x

---

## 13 License

Released under the **Apache 2.0 License**.  
See [LICENSE](LICENSE) for details.

