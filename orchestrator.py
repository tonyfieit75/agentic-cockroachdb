#!/usr/bin/env python3
import time
import json
import subprocess
from prometheus_api_client import PrometheusConnect

# === Configuration ===
NAMESPACE = "agentic-db"
CR_NAME = "crdb-prod"
PROM_URL = "http://prometheus:9090"

TARGET_TPS = 10000        # target throughput
TARGET_LAT = 5.0          # target P99 latency (ms)
BENCH_DURATION = "5m"     # benchmark run time per iteration
BENCH_WAREHOUSES = "1000" # tpcc workload scale
SLEEP_INTERVAL = 600      # seconds between tuning iterations

# Initialize Prometheus client
prom = PrometheusConnect(url=PROM_URL, disable_ssl=True)


# ------------------------------------------------------------
# 🧠 PLANNER AGENT
# ------------------------------------------------------------
def planner_agent(current_tps, current_lat, current_nodes):
    """
    Planner Agent decides what next action to take.
    """
    if current_tps < TARGET_TPS * 0.95:
        return "scale_up", f"TPS below target ({current_tps:.2f} < {TARGET_TPS}), planning to add nodes."
    elif current_lat > TARGET_LAT * 1.2:
        return "optimize", f"Latency too high ({current_lat:.2f} ms > {TARGET_LAT} ms), trigger optimization."
    else:
        return "hold", f"SLA stable ({current_tps:.2f} TPS @ {current_lat:.2f} ms). Holding configuration."


# ------------------------------------------------------------
# 📊 FEEDBACK AGENT
# ------------------------------------------------------------
def get_prometheus_metrics():
    """Query Prometheus for TPS and latency metrics."""
    try:
        tps_query = 'rate(sql_exec_count[1m])'
        lat_query = 'histogram_quantile(0.99, rate(sql_exec_latency_bucket[1m]))'
        tps_result = prom.custom_query(tps_query)
        lat_result = prom.custom_query(lat_query)
        if not tps_result or not lat_result:
            raise ValueError("Empty Prometheus result")

        tps = float(tps_result[0]["value"][1])
        lat = float(lat_result[0]["value"][1]) * 1000  # seconds → ms
        return tps, lat
    except Exception as e:
        print(f"⚠️ Failed to fetch metrics: {e}")
        return 0.0, 9999.0


# ------------------------------------------------------------
# 🙋 HUMAN-IN-THE-LOOP AGENT
# ------------------------------------------------------------
def human_approval(action, reason):
    """
    Human oversight for safety-critical changes.
    Future: integrate with Slack, Telegram, or WhatsApp API.
    """
    print(f"\n🧠 Planner Decision: {reason}")
    if action in ["scale_up", "optimize"]:
        decision = input(f"Approve action '{action}'? (y/n): ").strip().lower()
        if decision != "y":
            print("🚫 Human vetoed this action. Skipping.")
            return False
    return True


# ------------------------------------------------------------
# ⚙️ EXECUTION AGENT
# ------------------------------------------------------------
def execute_action(action, current_nodes):
    """Apply tuning or scaling actions."""
    if action == "scale_up":
        new_nodes = current_nodes + 1
        print(f"🔧 Scaling CockroachDB nodes: {current_nodes} → {new_nodes}")
        patch = json.dumps({"spec": {"nodes": new_nodes}})
        subprocess.run([
            "oc", "patch", "crdbcluster", CR_NAME,
            "--type=merge", "-p", patch,
            "-n", NAMESPACE
        ], check=False)
        return new_nodes

    elif action == "optimize":
        print("⚙️ Running CockroachDB optimization (rebalance / config tweaks)...")
        # Placeholder: implement actual tuning logic here
        return current_nodes

    else:
        print("✅ No change required.")
        return current_nodes


# ------------------------------------------------------------
# 🚀 MAIN CONTROL LOOP
# ------------------------------------------------------------
def main():
    current_nodes = 5
    print("🚀 Starting Agentic CockroachDB Orchestrator loop...")

    while True:
        # Step 1: Benchmark
        print("\n🔍 Launching CockroachDB TPCC benchmark job...")
        run_benchmark()

        # Step 2: Measure
        time.sleep(30)
        tps, lat = get_prometheus_metrics()
        print(f"📊 Current TPS = {tps:.2f}, P99 Latency = {lat:.2f} ms")

        # Step 3: Plan
        action, reason = planner_agent(tps, lat, current_nodes)

        # Step 4: Human approval
        if human_approval(action, reason):
            current_nodes = execute_action(action, current_nodes)
        else:
            print("⏭️ Skipping action due to human veto.")

        # Step 5: Evaluate loop
        if tps >= TARGET_TPS and lat <= TARGET_LAT:
            print("✅ SLA achieved! Finalizing configuration.")
            break

        print(f"⏳ Waiting {SLEEP_INTERVAL/60:.1f} min before next iteration...")
        time.sleep(SLEEP_INTERVAL)


def run_benchmark():
    """Launch a transient benchmark Job in OpenShift using your CockroachDB s390x image."""
    job_manifest = f"""
apiVersion: batch/v1
kind: Job
metadata:
  generateName: tpcc-bench-
  namespace: {NAMESPACE}
spec:
  backoffLimit: 0
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: workload
          image: quay.io/tonyfieit75/cockroachdb-s390x:23.1.2
          command:
            - /cockroach/cockroach
          args:
            - workload
            - run
            - tpcc
            - --warehouses={BENCH_WAREHOUSES}
            - --duration={BENCH_DURATION}
            - --tolerate-errors
            - --host={CR_NAME}-public
"""
    with open("/tmp/benchmark-job.yaml", "w") as f:
        f.write(job_manifest)

    subprocess.run(["oc", "apply", "-f", "/tmp/benchmark-job.yaml"], check=True)
    print("✅ Benchmark job submitted.")
    subprocess.run(["oc", "wait", "--for=condition=complete", "jobs", "-n", NAMESPACE, "--timeout=10m"])


if __name__ == "__main__":
    main()

