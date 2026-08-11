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


# 1. sqlite3 import 추가
do(1,
'import subprocess',
'import subprocess\nimport sqlite3')

# 2. HISTORY_DB 경로 + 초기화 함수 추가 (OUTPUT_DIR 바로 뒤)
do(2,
'OUTPUT_DIR = "/output"',
'''OUTPUT_DIR = "/output"
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


init_history_db()''')

# 3. 히스토리 API 3개 추가 (job_stream 라우트 바로 앞)
do(3,
'@app.route("/api/jobs/<mode>/stream")\ndef job_stream(mode):',
'''@app.route("/api/history", methods=["GET"])
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


@app.route("/api/jobs/<mode>/stream")
def job_stream(mode):''')

print("all done")
