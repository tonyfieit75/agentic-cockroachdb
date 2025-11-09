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


def run_benchmark():
    """Launch a transient benchmark Job in OpenShift using your CockroachDB s390x image."""
    print("🔍 Launching CockroachDB TPCC benchmark job...")

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
    # Wait for completion
    subprocess.run(["oc", "wait", "--for=condition=complete", "jobs", "-l", "job-name", "-n", NAMESPACE, "--timeout=10m"])


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


def tune_cockroachdb():
    """Example of a simple tuning action."""
    print("⚙️ Applying CockroachDB tuning patch...")
    patch = '{"spec":{"nodes":5}}'
    subprocess.run([
        "oc", "patch", "crdbcluster", CR_NAME,
        "--type=merge", "-p", patch,
        "-n", NAMESPACE
    ], check=False)


# === Main control loop ===
if __name__ == "__main__":
    print("🚀 Starting agentic CockroachDB orchestrator loop...")

    while True:
        run_benchmark()
        time.sleep(30)  # small delay before reading metrics

        tps, lat = get_prometheus_metrics()
        print(f"📊 Current TPS = {tps:.2f}, P99 Latency = {lat:.2f} ms")

        if tps >= TARGET_TPS and lat <= TARGET_LAT:
            print("✅ SLA achieved! Finalizing configuration.")
            break

        print("🔁 SLA not met. Initiating tuning step...")
        tune_cockroachdb()
        print(f"⏳ Sleeping {SLEEP_INTERVAL/60:.1f} min before next iteration...")
        time.sleep(SLEEP_INTERVAL)

