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


# 1. _job_summary에 suspended 필드 추가
do(1,
'''    return {
        "completions": completions,
        "total": total,
        "parallelism": job.spec.parallelism,
        "complete": complete,
        "duration_seconds": duration,
    }''',
'''    return {
        "completions": completions,
        "total": total,
        "parallelism": job.spec.parallelism,
        "complete": complete,
        "duration_seconds": duration,
        "suspended": bool(job.spec.suspend),
    }''')

# 2. 일시정지/재작업 엔드포인트 추가
do(2,
'EVENT_REASON_LABELS = {',
'''@app.route("/api/jobs/<mode>/pause", methods=["POST"])
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


EVENT_REASON_LABELS = {''')

print("all done")
