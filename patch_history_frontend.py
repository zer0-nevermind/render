path = "templates/index.html"


def do(step, old, new, count=1):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    n = content.count(old)
    assert n >= count, f"step {step}: not found (found {n})"
    content = content.replace(old, new, count)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"step{step} ok (saved)")


# 1. 페이지 로드시 서버에서 히스토리 불러오기
do(1,
'''renderHistory();
function setSubmitDisabled(disabled) {''',
'''renderHistory();
function loadHistoryFromServer() {
  fetch('api/history').then(r => r.json()).then(rows => {
    rows.forEach(row => {
      const entry = {
        id: ++historyCounter,
        mode: row.mode,
        name: row.name || '-',
        workers: row.workers != null ? row.workers : '-',
        progress: `${row.completions || 0} / ${row.total_frames || 0}`,
        status: row.status || 'RUNNING',
        duration: row.duration_seconds != null ? `${row.duration_seconds}s` : '-',
        completions: row.completions || 0,
        total: row.total_frames || 0,
        runId: row.run_id,
      };
      jobHistory.unshift(entry);
    });
    renderHistory();
  }).catch(() => {});
}
loadHistoryFromServer();
function setSubmitDisabled(disabled) {''')

# 2. 작업 시작 시 서버에 기록 저장
do(2,
'''      entry.workers = startInfo.parallelism;
      entry.runId = startInfo.run_id;
      entry.progress = `0 / ${startInfo.total_frames}`;
      currentParallelism = startInfo.parallelism;
      renderHistory();''',
'''      entry.workers = startInfo.parallelism;
      entry.runId = startInfo.run_id;
      entry.progress = `0 / ${startInfo.total_frames}`;
      currentParallelism = startInfo.parallelism;
      renderHistory();
      fetch('api/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          run_id: startInfo.run_id,
          mode: mode,
          name: entry.name,
          total_frames: startInfo.total_frames,
          workers: startInfo.parallelism,
        }),
      }).catch(() => {});''')

# 3. 완료 시 서버 기록 업데이트
do(3,
'''          entry.status = 'COMPLETED';
          entry.duration = `${data.duration_seconds}s`;
          renderHistory();''',
'''          entry.status = 'COMPLETED';
          entry.duration = `${data.duration_seconds}s`;
          renderHistory();
          fetch(`api/history/${entry.runId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              status: 'COMPLETED',
              duration_seconds: data.duration_seconds,
              completions: data.completions,
              total: data.total,
            }),
          }).catch(() => {});''')

# 4. 오류 시 서버 기록 업데이트
do(4,
'''        entry.status = 'ERROR';
        renderHistory();
        logMsg('스트림 연결 오류 발생');''',
'''        entry.status = 'ERROR';
        renderHistory();
        if (entry.runId) {
          fetch(`api/history/${entry.runId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'ERROR' }),
          }).catch(() => {});
        }
        logMsg('스트림 연결 오류 발생');''')

print("all done")
