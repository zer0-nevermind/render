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


do(1,
'EVENT_REASON_LABELS = {',
'''@app.route("/api/jobs/<mode>/cancel", methods=["POST"])
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


EVENT_REASON_LABELS = {''')

print("all done")
