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


# 1. HTML - placeholder를 실제 표시 요소로 교체
do(1,
'<div id="resource-monitor-wrap"><span class="placeholder" style="font-size:11px;">준비 중</span></div>',
'''<div id="resource-monitor-wrap">
      <div style="font-size:11px; margin-bottom:4px;">CPU <span id="metric-cpu-text">-</span></div>
      <div class="bar-track"><div class="bar-fill single" id="metric-cpu-bar" style="width:0%"></div></div>
      <div style="font-size:11px; margin:8px 0 4px;">메모리 <span id="metric-mem-text">-</span></div>
      <div class="bar-track"><div class="bar-fill distributed" id="metric-mem-bar" style="width:0%"></div></div>
    </div>''')

# 2. JS - 폴링 함수 추가 (loadHistoryFromServer 호출 뒤)
do(2,
'loadHistoryFromServer();',
'''loadHistoryFromServer();
function updateMetricsDisplay(data) {
  const wrap = document.getElementById('resource-monitor-wrap');
  if (!data || !data.available) {
    wrap.innerHTML = '<span class="placeholder" style="font-size:11px;">metrics-server 사용 불가</span>';
    return;
  }
  const cpuPct = data.cpu_total_cores > 0 ? Math.min(100, Math.round((data.cpu_used_cores / data.cpu_total_cores) * 100)) : 0;
  const memGbUsed = (data.memory_used_mi / 1024).toFixed(1);
  const memGbTotal = (data.memory_total_mi / 1024).toFixed(1);
  const memPct = data.memory_total_mi > 0 ? Math.min(100, Math.round((data.memory_used_mi / data.memory_total_mi) * 100)) : 0;
  const cpuTextEl = document.getElementById('metric-cpu-text');
  const cpuBarEl = document.getElementById('metric-cpu-bar');
  const memTextEl = document.getElementById('metric-mem-text');
  const memBarEl = document.getElementById('metric-mem-bar');
  if (cpuTextEl) cpuTextEl.innerText = `${data.cpu_used_cores.toFixed(2)} / ${data.cpu_total_cores.toFixed(1)} 코어 (${cpuPct}%)`;
  if (cpuBarEl) cpuBarEl.style.width = cpuPct + '%';
  if (memTextEl) memTextEl.innerText = `${memGbUsed} / ${memGbTotal} GB (${memPct}%)`;
  if (memBarEl) memBarEl.style.width = memPct + '%';
}
function pollMetrics() {
  fetch('api/metrics').then(r => r.json()).then(updateMetricsDisplay).catch(() => {});
}
pollMetrics();
setInterval(pollMetrics, 3000);''')

print("all done")
