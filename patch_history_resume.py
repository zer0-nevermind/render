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


# 1. resumeRunningJob 함수 추가 (loadHistoryFromServer 바로 앞)
do(1,
'function loadHistoryFromServer() {',
'''function resumeRunningJob(entry, createdAt) {
  const mode = entry.mode;
  const jobStartTime = createdAt ? createdAt * 1000 : Date.now();
  logMsg(`재접속: 진행 중이던 '${entry.name}' 작업 상태를 다시 가져옵니다.`);
  startPreviewPolling(entry.runId);
  startTopologyPolling(mode);
  const es = new EventSource(`api/jobs/${mode}/stream`);
  let lastCompletions = -1;
  es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.exists === false) {
      es.close();
      stopPreviewPolling();
      stopTopologyPolling();
      entry.status = 'ERROR';
      renderHistory();
      fetch(`api/history/${entry.runId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'ERROR' }),
      }).catch(() => {});
      logMsg(`'${entry.name}' 작업을 더 이상 클러스터에서 찾을 수 없습니다.`);
      return;
    }
    if (data.events && data.events.length) {
      data.events.forEach(ev => logMsg(`[${ev.pod}] ${ev.label}`));
    }
    const pct = Math.round((data.completions / data.total) * 100);
    setProgressRing(pct);
    document.getElementById('progress-job-name').innerText = JOB_NAMES[mode];
    document.getElementById('progress-remaining').innerText = `${data.total - data.completions} frames`;
    const elapsedSec = (Date.now() - jobStartTime) / 1000;
    document.getElementById('progress-elapsed').innerText = `${Math.round(elapsedSec)}s`;
    document.getElementById('status-text').innerText = `${data.completions} / ${data.total} 프레임 렌더링 완료`;
    entry.progress = `${data.completions} / ${data.total}`;
    entry.completions = data.completions;
    entry.total = data.total;
    renderHistory();
    if (data.completions !== lastCompletions) {
      logMsg(`완료된 프레임: ${data.completions} / ${data.total}`);
      lastCompletions = data.completions;
    }
    if (data.complete) {
      es.close();
      stopPreviewPolling();
      stopTopologyPolling();
      document.getElementById('status-text').innerText = `${data.duration_seconds}초 만에 완료`;
      document.getElementById(`time-${mode}`).innerText = `${data.duration_seconds}s`;
      durations[mode] = data.duration_seconds;
      updateBars();
      updateSpeedup();
      entry.status = 'COMPLETED';
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
      }).catch(() => {});
      logMsg(`전체 렌더링 완료! 총 ${data.duration_seconds}초 소요`);
      stats.completedJobs++;
      updateStatsKpi();
    }
  };
  es.onerror = () => {
    es.close();
    stopPreviewPolling();
    stopTopologyPolling();
    entry.status = 'ERROR';
    renderHistory();
    fetch(`api/history/${entry.runId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'ERROR' }),
    }).catch(() => {});
    logMsg('재접속한 스트림에서 연결 오류 발생');
  };
}
function loadHistoryFromServer() {''')

# 2. 로드된 항목 중 RUNNING 상태면 재접속 트리거
do(2,
'''      jobHistory.unshift(entry);
    });
    renderHistory();''',
'''      jobHistory.unshift(entry);
      if (entry.status === 'RUNNING') {
        resumeRunningJob(entry, row.created_at);
      }
    });
    renderHistory();''')

print("all done")
