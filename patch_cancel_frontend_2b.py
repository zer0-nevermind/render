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


do(5,
'''    <div class="status-line" id="status-text">대기 중</div>
    <div class="status-line" id="job-desc-text" style="margin-top:4px;">Job 제출 시 Kubernetes가 선택한 워커 수만큼 Pod를 자동 생성해 24개 프레임을 나눠 렌더링합니다.</div>
  </div>

  <div class="panel col-8 left-col-panel">
    <div class="panel-title"><span>현황 요약</span></div>''',
'''    <div class="status-line" id="status-text">대기 중</div>
    <div class="status-line" id="job-desc-text" style="margin-top:4px;">Job 제출 시 Kubernetes가 선택한 워커 수만큼 Pod를 자동 생성해 24개 프레임을 나눠 렌더링합니다.</div>
    </div>
    <div style="flex-shrink:0; display:flex; align-items:center; gap:16px; padding-left:16px; border-left:1px solid var(--panel-border);">
      <div id="progress-ring" style="width:80px; height:80px; border-radius:50%; background:conic-gradient(var(--blue) 0%, #22252b 0); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
        <div style="width:60px; height:60px; border-radius:50%; background:var(--panel-bg); display:flex; align-items:center; justify-content:center;">
          <span id="progress-ring-value" style="font-size:14px; font-weight:700;">0%</span>
        </div>
      </div>
      <div style="font-size:12px; line-height:1.9;">
        <div>작업: <span id="progress-job-name" style="color:var(--text); font-weight:600;">-</span></div>
        <div>경과 시간: <span id="progress-elapsed" style="color:var(--text); font-weight:600;">-</span></div>
        <div>남은 프레임: <span id="progress-remaining" style="color:var(--text); font-weight:600;">-</span></div>
        <div>예상 완료: <span id="progress-eta" style="color:var(--text); font-weight:600;">-</span></div>
      </div>
    </div>
    </div>
  </div>

  <div class="panel col-8 left-col-panel">
    <div class="panel-title"><span>현황 요약</span></div>''')

print("step5 done")
