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


# 8. runJob - 취소 대상 등록 + 버튼 표시
do(8,
'''function runJob(mode, maxIter, totalFrames, centerX, centerY, entry, onDone) {
  document.getElementById('status-text').innerText = '작업 제출 중...';''',
'''function runJob(mode, maxIter, totalFrames, centerX, centerY, entry, onDone) {
  currentRunningMode = mode;
  currentRunningEntry = entry;
  showCancelButton(entry);
  document.getElementById('status-text').innerText = '작업 제출 중...';''')

# 9. runJob onmessage - exists===false 가드 추가
do(9,
'''      es.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.events && data.events.length) {''',
'''      es.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.exists === false) {
          es.close();
          stopPreviewPolling();
          stopTopologyPolling();
          entry.status = cancelRequested ? 'CANCELLED' : 'ERROR';
          const finalStatus = entry.status;
          cancelRequested = false;
          renderHistory();
          hideCancelButton();
          fetch(`api/history/${entry.runId}/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: finalStatus }),
          }).catch(() => {});
          logMsg(finalStatus === 'CANCELLED' ? `'${entry.name}' 작업이 취소되었습니다.` : `'${entry.name}' 작업을 더 이상 클러스터에서 찾을 수 없습니다.`);
          onDone();
          return;
        }
        if (data.events && data.events.length) {''')

# 10. runJob 완료 처리 - 취소 버튼 숨김
do(10,
'''          updateStatsKpi();
          onDone();
        }
      };
      es.onerror = () => {''',
'''          updateStatsKpi();
          hideCancelButton();
          onDone();
        }
      };
      es.onerror = () => {''')

# 11. runJob 오류 처리 - 취소 버튼 숨김
do(11,
'''        logMsg('스트림 연결 오류 발생');
        stats.errorJobs++;
        updateStatsKpi();
        onDone();
      };''',
'''        logMsg('스트림 연결 오류 발생');
        stats.errorJobs++;
        updateStatsKpi();
        hideCancelButton();
        onDone();
      };''')

# 12. resumeRunningJob - 취소 대상 등록 + 버튼 표시
do(12,
'''function resumeRunningJob(entry, createdAt) {
  const mode = entry.mode;
  const jobStartTime = createdAt ? createdAt * 1000 : Date.now();''',
'''function resumeRunningJob(entry, createdAt) {
  const mode = entry.mode;
  currentRunningMode = mode;
  currentRunningEntry = entry;
  showCancelButton(entry);
  const jobStartTime = createdAt ? createdAt * 1000 : Date.now();''')

# 13. resumeRunningJob exists===false 처리 - 취소 상태 반영
do(13,
'''    if (data.exists === false) {
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
    }''',
'''    if (data.exists === false) {
      es.close();
      stopPreviewPolling();
      stopTopologyPolling();
      entry.status = cancelRequested ? 'CANCELLED' : 'ERROR';
      const finalStatus = entry.status;
      cancelRequested = false;
      renderHistory();
      hideCancelButton();
      fetch(`api/history/${entry.runId}/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: finalStatus }),
      }).catch(() => {});
      logMsg(finalStatus === 'CANCELLED' ? `'${entry.name}' 작업이 취소되었습니다.` : `'${entry.name}' 작업을 더 이상 클러스터에서 찾을 수 없습니다.`);
      return;
    }''')

# 14. resumeRunningJob 완료 처리 - 취소 버튼 숨김
do(14,
'''      logMsg(`전체 렌더링 완료! 총 ${data.duration_seconds}초 소요`);
      stats.completedJobs++;
      updateStatsKpi();
    }
  };
  es.onerror = () => {''',
'''      logMsg(`전체 렌더링 완료! 총 ${data.duration_seconds}초 소요`);
      stats.completedJobs++;
      updateStatsKpi();
      hideCancelButton();
    }
  };
  es.onerror = () => {''')

# 15. resumeRunningJob 오류 처리 - 취소 버튼 숨김
do(15,
'''    entry.status = 'ERROR';
    renderHistory();
    fetch(`api/history/${entry.runId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'ERROR' }),
    }).catch(() => {});
    logMsg('재접속한 스트림에서 연결 오류 발생');
  };
}
function loadHistoryFromServer() {''',
'''    entry.status = 'ERROR';
    renderHistory();
    hideCancelButton();
    fetch(`api/history/${entry.runId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'ERROR' }),
    }).catch(() => {});
    logMsg('재접속한 스트림에서 연결 오류 발생');
  };
}
function loadHistoryFromServer() {''')

print("all done")
