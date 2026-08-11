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


# 1. HTML - 4개 버튼 항상 노출
do(1,
'''    <button id="btn-cancel" onclick="cancelCurrentJob()" style="display:none;">현재 작업 취소</button>
    <div class="stat-label" id="cancel-status" style="margin-top:8px;">실행 중인 작업 없음</div>''',
'''    <div style="display:flex; gap:8px; flex-wrap:wrap;">
      <button id="btn-pause" onclick="pauseCurrentJob()" disabled>일시정지</button>
      <button id="btn-resume" onclick="resumeCurrentJob()" disabled>재작업</button>
      <button id="btn-cancel" onclick="cancelCurrentJob()" disabled>작업 취소</button>
      <button id="btn-cancel-queued" onclick="cancelQueuedJob()" disabled>예약 취소</button>
    </div>
    <div class="stat-label" id="cancel-status" style="margin-top:8px;">실행 중인 작업 없음</div>''')

# 2. showCancelButton / hideCancelButton 교체 + 신규 함수 추가
do(2,
'''function showCancelButton(entry) {
  const btn = document.getElementById('btn-cancel');
  const status = document.getElementById('cancel-status');
  if (btn) btn.style.display = 'inline-block';
  if (status) status.innerText = `실행 중: ${entry.name}`;
}
function hideCancelButton() {
  const btn = document.getElementById('btn-cancel');
  const status = document.getElementById('cancel-status');
  if (btn) btn.style.display = 'none';
  if (status) status.innerText = '실행 중인 작업 없음';
  currentRunningMode = null;
  currentRunningEntry = null;
}''',
'''let currentJobPaused = false;
function updateControlButtons() {
  const hasJob = !!currentRunningEntry;
  const btnPause = document.getElementById('btn-pause');
  const btnResume = document.getElementById('btn-resume');
  const btnCancel = document.getElementById('btn-cancel');
  const btnCancelQueued = document.getElementById('btn-cancel-queued');
  const status = document.getElementById('cancel-status');
  if (btnPause) btnPause.disabled = !hasJob || currentJobPaused;
  if (btnResume) btnResume.disabled = !hasJob || !currentJobPaused;
  if (btnCancel) btnCancel.disabled = !hasJob;
  if (btnCancelQueued) btnCancelQueued.disabled = pendingQueue.length === 0;
  if (status) {
    status.innerText = hasJob
      ? (currentJobPaused ? `일시정지됨: ${currentRunningEntry.name}` : `실행 중: ${currentRunningEntry.name}`)
      : '실행 중인 작업 없음';
  }
}
function showCancelButton(entry) {
  currentJobPaused = false;
  updateControlButtons();
}
function hideCancelButton() {
  currentRunningMode = null;
  currentRunningEntry = null;
  currentJobPaused = false;
  updateControlButtons();
}
function pauseCurrentJob() {
  if (!currentRunningMode) return;
  fetch(`api/jobs/${currentRunningMode}/pause`, { method: 'POST' })
    .then(r => r.json())
    .then(() => {
      currentJobPaused = true;
      updateControlButtons();
      logMsg('작업을 일시정지했습니다.');
    })
    .catch(() => logMsg('일시정지 요청 중 오류가 발생했습니다.'));
}
function resumeCurrentJob() {
  if (!currentRunningMode) return;
  fetch(`api/jobs/${currentRunningMode}/resume`, { method: 'POST' })
    .then(r => r.json())
    .then(() => {
      currentJobPaused = false;
      updateControlButtons();
      logMsg('작업을 재개했습니다.');
    })
    .catch(() => logMsg('재작업 요청 중 오류가 발생했습니다.'));
}
function cancelQueuedJob() {
  if (pendingQueue.length === 0) return;
  if (!confirm('대기열의 다음 예약 작업을 취소할까요?')) return;
  const removed = pendingQueue.shift();
  removed.entry.status = 'CANCELLED';
  renderHistory();
  updateQueueKpi();
  updateControlButtons();
  logMsg(`'${removed.entry.name}' 예약 작업이 취소되었습니다.`);
}''')

# 3. submitJob() - 대기열 변경 시 버튼 상태 갱신
do(3,
'''  logMsg(`Job 큐에 추가됨 (대기 중 ${pendingQueue.length}개)`);
  updateQueueKpi();
  processQueue();''',
'''  logMsg(`Job 큐에 추가됨 (대기 중 ${pendingQueue.length}개)`);
  updateQueueKpi();
  updateControlButtons();
  processQueue();''')

# 4. processQueue() - 대기열 변경 시 버튼 상태 갱신
do(4,
'''function processQueue() {
  if (isRunning || pendingQueue.length === 0) return;
  const next = pendingQueue.shift();
  updateQueueKpi();
  isRunning = true;''',
'''function processQueue() {
  if (isRunning || pendingQueue.length === 0) return;
  const next = pendingQueue.shift();
  updateQueueKpi();
  updateControlButtons();
  isRunning = true;''')

# 5. runJob onmessage - suspended 상태 동기화
do(5,
'''          onDone();
          return;
        }
        if (data.events && data.events.length) {''',
'''          onDone();
          return;
        }
        if (typeof data.suspended === 'boolean' && data.suspended !== currentJobPaused) {
          currentJobPaused = data.suspended;
          updateControlButtons();
        }
        if (data.events && data.events.length) {''')

# 6. resumeRunningJob onmessage - suspended 상태 동기화
do(6,
'''      return;
    }
    if (data.events && data.events.length) {''',
'''      return;
    }
    if (typeof data.suspended === 'boolean' && data.suspended !== currentJobPaused) {
      currentJobPaused = data.suspended;
      updateControlButtons();
    }
    if (data.events && data.events.length) {''')

print("all done")
