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


# 1. 취소됨 배지 CSS
do(1,
'.status-badge.error { background: #3a1c1c; color: var(--red); }',
'''.status-badge.error { background: #3a1c1c; color: var(--red); }
  .status-badge.cancelled { background: #3a2f1c; color: var(--orange); }''')

# 2. STATUS_LABELS에 CANCELLED 추가
do(2,
"const STATUS_LABELS = { QUEUED: '대기', RUNNING: '실행중', COMPLETED: '완료', ERROR: '오류' };",
"const STATUS_LABELS = { QUEUED: '대기', RUNNING: '실행중', COMPLETED: '완료', ERROR: '오류', CANCELLED: '취소됨' };")

# 3. 전역 변수 + 취소 관련 함수 추가
do(3,
'let currentParallelism = 0;',
'''let currentParallelism = 0;
let currentRunningMode = null;
let currentRunningEntry = null;
let cancelRequested = false;
function showCancelButton(entry) {
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
}
function cancelCurrentJob() {
  if (!currentRunningMode) return;
  if (!confirm('현재 실행 중인 작업을 취소할까요?')) return;
  cancelRequested = true;
  fetch(`api/jobs/${currentRunningMode}/cancel`, { method: 'POST' })
    .then(r => r.json())
    .then(() => {
      logMsg('작업 취소 요청을 보냈습니다.');
    })
    .catch(() => {
      cancelRequested = false;
      logMsg('작업 취소 요청 중 오류가 발생했습니다.');
    });
}''')

print("all done")
