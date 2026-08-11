import os
import time
import json
import glob
import subprocess
import sqlite3
from flask import Flask, jsonify, Response, send_file, abort, request, render_template
from kubernetes import client, config

app = Flask(__name__)

NAMESPACE = "render-farm"
IMAGE = "192.168.2.75:5000/mandelbrot-worker:latest"
PVC_NAME = "render-output-pvc"
CONFIGMAP_NAME = "render-config"
OUTPUT_DIR = "/output"
HISTORY_DB = os.path.join(OUTPUT_DIR, "history.db")


def init_history_db():
    conn = sqlite3.connect(HISTORY_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_history (
            run_id TEXT PRIMARY KEY,
            mode TEXT,
            name TEXT,
            total_frames INTEGER,
            workers INTEGER,
            status TEXT,
            duration_seconds REAL,
            completions INTEGER,
            created_at REAL
        )
    """)
    conn.commit()
    conn.close()


init_history_db()
CPU_REQUEST_PER_POD = 0.5  # matches the "500m" request in build_job()

config.load_incluster_config()
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()
metrics_api = client.CustomObjectsApi()

JOB_SPECS = {
    "single": {"name": "render-single"},
    "distributed": {"name": "render-distributed"},
}


def parse_cpu(qty):
    """Parse a k8s CPU quantity string ('4', '4000m', '3500m', '1059693298n', '77356u') into cores as float."""
    if qty is None:
        return 0.0
    qty = str(qty)
    if qty.endswith("n"):
        return float(qty[:-1]) / 1_000_000_000.0
    if qty.endswith("u"):
        return float(qty[:-1]) / 1_000_000.0
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
    return float(qty) / (1024 * 1024)


def get_cluster_cpu_capacity():
    """Sum allocatable CPU across schedulable (non-tainted) nodes."""
    nodes = core_v1.list_node()
    total = 0.0
    for n in nodes.items:
        taints = n.spec.taints or []
        schedulable = not any(t.effect == "NoSchedule" for t in taints)
        if not schedulable:
            continue
        allocatable = (n.status.allocatable or {}).get("cpu")
        total += parse_cpu(allocatable)
    return total


def build_job(mode, total_frames, parallelism, run_id):
    name = JOB_SPECS[mode]["name"]
    container = client.V1Container(
        name="worker",
        image=IMAGE,
        env=[client.V1EnvVar(name="OUTPUT_DIR", value=os.path.join(OUTPUT_DIR, run_id))],
        env_from=[client.V1EnvFromSource(
            config_map_ref=client.V1ConfigMapEnvSource(name=CONFIGMAP_NAME)
        )],
        resources=client.V1ResourceRequirements(
            requests={"cpu": "500m", "memory": "256Mi"},
            limits={"cpu": "1", "memory": "512Mi"},
        ),
        volume_mounts=[client.V1VolumeMount(name="output", mount_path=OUTPUT_DIR)],
    )
    pod_spec = client.V1PodSpec(
        restart_policy="Never",
        containers=[container],
        volumes=[client.V1Volume(
            name="output",
            persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(claim_name=PVC_NAME),
        )],
    )
    template = client.V1PodTemplateSpec(spec=pod_spec)
    job_spec = client.V1JobSpec(
        completion_mode="Indexed",
        completions=total_frames,
        parallelism=parallelism,
        backoff_limit=2,
        template=template,
    )
    return client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(name=name, namespace=NAMESPACE),
        spec=job_spec,
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/nodes")
def list_nodes():
    nodes = core_v1.list_node()
    result = []
    for n in nodes.items:
        taints = n.spec.taints or []
        schedulable = not any(t.effect == "NoSchedule" for t in taints)
        result.append({
            "name": n.metadata.name,
            "schedulable": schedulable,
            "allocatable_cpu": parse_cpu((n.status.allocatable or {}).get("cpu")),
        })
    result.sort(key=lambda x: x["name"])
    return jsonify(result)


@app.route("/api/cluster/capacity")
def cluster_capacity():
    total_cpu = get_cluster_cpu_capacity()
    return jsonify({
        "total_allocatable_cpu": total_cpu,
        "cpu_per_pod": CPU_REQUEST_PER_POD,
        "max_concurrent_pods": int(total_cpu // CPU_REQUEST_PER_POD),
    })


@app.route("/api/metrics")
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


@app.route("/api/jobs/<mode>/start", methods=["POST"])
def start_job(mode):
    if mode not in JOB_SPECS:
        abort(404)

    max_iter = request.args.get("max_iter")
    total_frames = request.args.get("total_frames", "24")
    try:
        total_frames = int(total_frames)
        if total_frames < 1:
            raise ValueError
    except ValueError:
        return jsonify({"error": "total_frames must be a positive integer"}), 400

    configmap_patch = {"TOTAL_FRAMES": str(total_frames)}
    if max_iter:
        try:
            int(max_iter)
        except ValueError:
            return jsonify({"error": "max_iter must be an integer"}), 400
        configmap_patch["MAX_ITER"] = str(max_iter)

    center_x = request.args.get("center_x")
    center_y = request.args.get("center_y")
    if center_x:
        try:
            float(center_x)
        except ValueError:
            return jsonify({"error": "center_x must be a number"}), 400
        configmap_patch["CENTER_X"] = str(center_x)
    if center_y:
        try:
            float(center_y)
        except ValueError:
            return jsonify({"error": "center_y must be a number"}), 400
        configmap_patch["CENTER_Y"] = str(center_y)

    core_v1.patch_namespaced_config_map(
        name=CONFIGMAP_NAME,
        namespace=NAMESPACE,
        body={"data": configmap_patch},
    )

    if mode == "single":
        parallelism = 1
    else:
        total_cpu = get_cluster_cpu_capacity()
        max_parallel = max(1, int(total_cpu // CPU_REQUEST_PER_POD))
        parallelism = min(total_frames, max_parallel)

    name = JOB_SPECS[mode]["name"]
    try:
        batch_v1.delete_namespaced_job(
            name=name, namespace=NAMESPACE,
            body=client.V1DeleteOptions(propagation_policy="Foreground"),
        )
        for _ in range(30):
            try:
                batch_v1.read_namespaced_job(name=name, namespace=NAMESPACE)
                time.sleep(1)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    break
                raise
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise

    run_id = f"{mode}-{int(time.time())}"
    batch_v1.create_namespaced_job(
        namespace=NAMESPACE,
        body=build_job(mode, total_frames, parallelism, run_id),
    )
    return jsonify({"started": name, "total_frames": total_frames, "parallelism": parallelism, "run_id": run_id})


@app.route("/api/jobs/<mode>/cancel", methods=["POST"])
def cancel_job(mode):
    if mode not in JOB_SPECS:
        abort(404)
    name = JOB_SPECS[mode]["name"]
    try:
        batch_v1.delete_namespaced_job(
            name=name, namespace=NAMESPACE,
            body=client.V1DeleteOptions(propagation_policy="Foreground"),
        )
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise
        return jsonify({"error": "job not found"}), 404
    return jsonify({"cancelled": name})


@app.route("/api/jobs/<mode>/pause", methods=["POST"])
def pause_job(mode):
    if mode not in JOB_SPECS:
        abort(404)
    name = JOB_SPECS[mode]["name"]
    try:
        batch_v1.patch_namespaced_job(
            name=name, namespace=NAMESPACE,
            body={"spec": {"suspend": True}},
        )
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise
        return jsonify({"error": "job not found"}), 404
    return jsonify({"paused": name})


@app.route("/api/jobs/<mode>/resume", methods=["POST"])
def resume_job(mode):
    if mode not in JOB_SPECS:
        abort(404)
    name = JOB_SPECS[mode]["name"]
    try:
        batch_v1.patch_namespaced_job(
            name=name, namespace=NAMESPACE,
            body={"spec": {"suspend": False}},
        )
    except client.exceptions.ApiException as e:
        if e.status != 404:
            raise
        return jsonify({"error": "job not found"}), 404
    return jsonify({"resumed": name})


EVENT_REASON_LABELS = {
    "Scheduled": "Pod 스케줄링됨",
    "Pulling": "이미지 pull 중",
    "Pulled": "이미지 pull 완료",
    "Created": "컨테이너 생성됨",
    "Started": "컨테이너 시작됨",
}
def _job_pod_names(mode):
    name = JOB_SPECS[mode]["name"]
    pods = core_v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=f"job-name={name}",
    )
    return [p.metadata.name for p in pods.items]
def _job_events(mode, seen_uids):
    pod_names = set(_job_pod_names(mode))
    if not pod_names:
        return []
    events = core_v1.list_namespaced_event(namespace=NAMESPACE)
    new_events = []
    for e in events.items:
        if e.involved_object.kind != "Pod":
            continue
        if e.involved_object.name not in pod_names:
            continue
        if e.reason not in EVENT_REASON_LABELS:
            continue
        uid = e.metadata.uid
        if uid in seen_uids:
            continue
        seen_uids.add(uid)
        ts = e.last_timestamp or e.event_time
        new_events.append({
            "pod": e.involved_object.name,
            "reason": e.reason,
            "label": EVENT_REASON_LABELS[e.reason],
            "message": e.message,
            "time": ts.isoformat() if ts else None,
        })
    new_events.sort(key=lambda x: x["time"] or "")
    return new_events
POD_FAILURE_REASONS = {"ErrImagePull", "ImagePullBackOff", "CrashLoopBackOff"}


def _detect_pod_failure(name):
    try:
        pods = core_v1.list_namespaced_pod(
            namespace=NAMESPACE, label_selector=f"job-name={name}"
        )
    except client.exceptions.ApiException:
        return None
    for pod in pods.items:
        statuses = pod.status.container_statuses or []
        for cs in statuses:
            waiting = cs.state.waiting if cs.state else None
            if waiting and waiting.reason in POD_FAILURE_REASONS:
                return f"{pod.metadata.name}: {waiting.reason} ({waiting.message or ''})"
        if pod.status.phase == "Failed":
            return f"{pod.metadata.name}: Pod Failed"
    return None


def _job_summary(mode):
    name = JOB_SPECS[mode]["name"]
    job = batch_v1.read_namespaced_job_status(name=name, namespace=NAMESPACE)
    total = job.spec.completions
    completions = job.status.succeeded or 0
    complete = job.status.completion_time is not None
    duration = None
    if job.status.start_time and job.status.completion_time:
        duration = (job.status.completion_time - job.status.start_time).total_seconds()
    pod_error = None if complete else _detect_pod_failure(name)
    return {
        "completions": completions,
        "total": total,
        "parallelism": job.spec.parallelism,
        "complete": complete,
        "duration_seconds": duration,
        "suspended": bool(job.spec.suspend),
        "pod_error": pod_error,
        "failed": bool(pod_error),
    }


@app.route("/api/jobs/<mode>/status")
def job_status(mode):
    if mode not in JOB_SPECS:
        abort(404)
    try:
        return jsonify({"exists": True, **_job_summary(mode)})
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return jsonify({"exists": False})
        raise


@app.route("/api/jobs/<mode>/pods")
def job_pods(mode):
    if mode not in JOB_SPECS:
        abort(404)
    name = JOB_SPECS[mode]["name"]
    pods = core_v1.list_namespaced_pod(
        namespace=NAMESPACE,
        label_selector=f"job-name={name}",
    )
    result = []
    for pod in pods.items:
        index = pod.metadata.labels.get("batch.kubernetes.io/job-completion-index", "?")
        result.append({
            "pod": pod.metadata.name,
            "index": index,
            "phase": pod.status.phase,
            "node": pod.spec.node_name,
        })

    def sort_key(p):
        try:
            return int(p["index"])
        except (TypeError, ValueError):
            return 999

    result.sort(key=sort_key)
    return jsonify(result)


@app.route("/api/history", methods=["GET"])
def get_history():
    conn = sqlite3.connect(HISTORY_DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM job_history ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/history", methods=["POST"])
def create_history():
    data = request.get_json(force=True)
    run_id = data.get("run_id")
    if not run_id:
        return jsonify({"error": "run_id is required"}), 400
    conn = sqlite3.connect(HISTORY_DB)
    conn.execute(
        "INSERT OR REPLACE INTO job_history "
        "(run_id, mode, name, total_frames, workers, status, duration_seconds, completions, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id, data.get("mode"), data.get("name"), data.get("total_frames"),
         data.get("workers"), "RUNNING", None, 0, time.time()),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/history/<run_id>/complete", methods=["POST"])
def complete_history(run_id):
    data = request.get_json(force=True)
    conn = sqlite3.connect(HISTORY_DB)
    conn.execute(
        "UPDATE job_history SET status = ?, duration_seconds = ?, completions = ? WHERE run_id = ?",
        (data.get("status", "COMPLETED"), data.get("duration_seconds"), data.get("completions"), run_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/history/clear", methods=["POST"])
def clear_history():
    conn = sqlite3.connect(HISTORY_DB)
    running = conn.execute(
        "SELECT COUNT(*) FROM job_history WHERE status = 'RUNNING'"
    ).fetchone()[0]
    if running > 0:
        conn.close()
        return jsonify({"error": "실행 중인 작업이 있어 초기화할 수 없습니다"}), 409
    conn.execute("DELETE FROM job_history")
    conn.commit()
    conn.close()
    return jsonify({"ok": True})
@app.route("/api/jobs/<mode>/stream")
def job_stream(mode):
    if mode not in JOB_SPECS:
        abort(404)

    def generate():
        seen_uids = set()
        while True:
            try:
                payload = _job_summary(mode)
            except client.exceptions.ApiException as e:
                if e.status == 404:
                    yield f"data: {json.dumps({'exists': False})}\n\n"
                    break
                raise
            try:
                payload["events"] = _job_events(mode, seen_uids)
            except client.exceptions.ApiException:
                payload["events"] = []
            yield f"data: {json.dumps(payload)}\n\n"
            if payload["complete"]:
                break
            if payload.get("failed"):
                try:
                    batch_v1.delete_namespaced_job(
                        name=JOB_SPECS[mode]["name"], namespace=NAMESPACE,
                        body=client.V1DeleteOptions(propagation_policy="Foreground"),
                    )
                except client.exceptions.ApiException:
                    pass
                break
            time.sleep(1)

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/encode", methods=["POST"])
def encode_video():
    run_id = request.args.get("run_id")
    if not run_id:
        return jsonify({"error": "run_id is required"}), 400
    try:
        total = int(request.args.get("total"))
    except (TypeError, ValueError):
        return jsonify({"error": "total must be an integer"}), 400
    run_dir = os.path.join(OUTPUT_DIR, run_id)
    completions = len(glob.glob(os.path.join(run_dir, "frame_*.png")))
    if completions < total:
        return jsonify({
            "error": f"run '{run_id}' is not complete yet",
            "completions": completions,
            "total": total,
        }), 409
    frames_glob = os.path.join(run_dir, "frame_%04d.png")
    output_path = os.path.join(run_dir, "render.mp4")
    cmd = [
        "ffmpeg", "-y", "-framerate", "24",
        "-i", frames_glob,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return jsonify({"error": result.stderr}), 500
    return jsonify({"video": "render.mp4"})


@app.route("/api/frames/latest")
def latest_frame():
    run_id = request.args.get("run_id")
    search_dir = os.path.join(OUTPUT_DIR, run_id) if run_id else OUTPUT_DIR
    frames = sorted(
        glob.glob(os.path.join(search_dir, "frame_*.png")),
        key=os.path.getmtime,
    )
    if not frames:
        abort(404)
    return send_file(frames[-1], mimetype="image/png")


@app.route("/api/video")
def get_video():
    run_id = request.args.get("run_id")
    search_dir = os.path.join(OUTPUT_DIR, run_id) if run_id else OUTPUT_DIR
    path = os.path.join(search_dir, "render.mp4")
    if not os.path.exists(path):
        abort(404)
    return send_file(path, mimetype="video/mp4")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
