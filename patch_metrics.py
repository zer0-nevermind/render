path = "app.py"


def do(step, old, new, count=1):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    n = content.count(old)
    assert n >= count, f"step {step}: not found (found {n})"
    content = content.replace(old, new, count)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"step{step} ok (saved)")


# 1. CustomObjectsApi 클라이언트 추가
do(1,
'''batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()''',
'''batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()
metrics_api = client.CustomObjectsApi()''')

# 2. 메모리 파싱 헬퍼 추가
do(2,
'''def parse_cpu(qty):
    """Parse a k8s CPU quantity string ('4', '4000m', '3500m') into cores as float."""
    if qty is None:
        return 0.0
    qty = str(qty)
    if qty.endswith("m"):
        return float(qty[:-1]) / 1000.0
    return float(qty)''',
'''def parse_cpu(qty):
    """Parse a k8s CPU quantity string ('4', '4000m', '3500m') into cores as float."""
    if qty is None:
        return 0.0
    qty = str(qty)
    if qty.endswith("m"):
        return float(qty[:-1]) / 1000.0
    return float(qty)
def parse_memory_mi(qty):
    """Parse a k8s memory quantity string ('2080Mi', '2Gi', '512Ki') into MiB as float."""
    if qty is None:
        return 0.0
    qty = str(qty)
    if qty.endswith("Ki"):
        return float(qty[:-2]) / 1024.0
    if qty.endswith("Mi"):
        return float(qty[:-2])
    if qty.endswith("Gi"):
        return float(qty[:-2]) * 1024.0
    return float(qty) / (1024 * 1024)''')

# 3. /api/metrics 엔드포인트 추가
do(3,
'@app.route("/api/jobs/<mode>/start", methods=["POST"])',
'''@app.route("/api/metrics")
def cluster_metrics():
    try:
        node_metrics = metrics_api.list_cluster_custom_object(
            group="metrics.k8s.io", version="v1beta1", plural="nodes",
        )
    except client.exceptions.ApiException:
        return jsonify({"available": False})
    cpu_used = 0.0
    mem_used = 0.0
    for item in node_metrics.get("items", []):
        usage = item.get("usage", {})
        cpu_used += parse_cpu(usage.get("cpu"))
        mem_used += parse_memory_mi(usage.get("memory"))
    total_cpu = get_cluster_cpu_capacity()
    total_mem = 0.0
    for n in core_v1.list_node().items:
        taints = n.spec.taints or []
        schedulable = not any(t.effect == "NoSchedule" for t in taints)
        if not schedulable:
            continue
        total_mem += parse_memory_mi((n.status.allocatable or {}).get("memory"))
    return jsonify({
        "available": True,
        "cpu_used_cores": round(cpu_used, 2),
        "cpu_total_cores": round(total_cpu, 2),
        "memory_used_mi": round(mem_used, 0),
        "memory_total_mi": round(total_mem, 0),
    })


@app.route("/api/jobs/<mode>/start", methods=["POST"])''')

print("all done")
