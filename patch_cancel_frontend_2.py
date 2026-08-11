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


# 4. 작업 제출 패널 - 우측에 진행률 위젯 자리를 위한 래핑 시작
do(4,
'''  <div class="panel col-8 left-col-panel">
    <div class="panel-title"><span>작업 제출</span></div>
    <div style="display:flex; gap:24px; flex-wrap:wrap; align-items:flex-end;">''',
'''  <div class="panel col-8 left-col-panel">
    <div class="panel-title"><span>작업 제출</span></div>
    <div style="display:flex; justify-content:space-between; gap:24px; flex-wrap:wrap;">
    <div style="flex:1; min-width:280px;">
    <div style="display:flex; gap:24px; flex-wrap:wrap; align-items:flex-end;">''')

# 5. 작업 제출 패널 - 래핑 닫고 진행률 위젯 삽입
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

# 6. 속도향상 + 소요시간비교 통합, 빈 자리에 리소스 모니터링 placeholder
do(6,
'''  <div class="panel col-2 left-col-panel">
    <div class="panel-title"><span>속도 향상</span></div>
    <div class="stat-value" id="speedup-value" style="font-size:28px;">-</div>
    <div class="stat-label">분산 vs 단일</div>
  </div>
  <div class="panel col-2 left-col-panel">
    <div class="panel-title"><span>소요시간 비교</span></div>
    <div class="bar-row">
      <div class="label"><span>단일 (워커 1대)</span><span id="time-single">-</span></div>
      <div class="bar-track"><div class="bar-fill single" id="bar-single" style="width:0%"></div></div>
    </div>
    <div class="bar-row">
      <div class="label"><span>분산 (워커 6대)</span><span id="time-distributed">-</span></div>
      <div class="bar-track"><div class="bar-fill distributed" id="bar-distributed" style="width:0%"></div></div>
    </div>
  </div>''',
'''  <div class="panel col-2 left-col-panel">
    <div class="panel-title"><span>소요시간 비교</span></div>
    <div style="display:flex; align-items:baseline; gap:8px; margin-bottom:10px;">
      <span class="stat-value" id="speedup-value" style="font-size:22px;">-</span>
      <span class="stat-label">분산 vs 단일 배속</span>
    </div>
    <div class="bar-row">
      <div class="label"><span>단일 (워커 1대)</span><span id="time-single">-</span></div>
      <div class="bar-track"><div class="bar-fill single" id="bar-single" style="width:0%"></div></div>
    </div>
    <div class="bar-row">
      <div class="label"><span>분산 (워커 6대)</span><span id="time-distributed">-</span></div>
      <div class="bar-track"><div class="bar-fill distributed" id="bar-distributed" style="width:0%"></div></div>
    </div>
  </div>
  <div class="panel col-2 left-col-panel">
    <div class="panel-title"><span>리소스 모니터링</span></div>
    <div id="resource-monitor-wrap"><span class="placeholder" style="font-size:11px;">준비 중</span></div>
  </div>''')

# 7. 워커 Pod 현황 - 진행률 섹션 제거, 취소 UI로 교체
do(7,
'''  <div class="panel col-4 left-col-panel">
    <div class="panel-title"><span>워커 Pod 현황</span></div>
    <div class="task-grid" id="pod-fleet-grid" style="max-width:none;"></div>
    <div class="stat-label" id="cpu-usage-pods" style="margin-top:10px;">실행 중 Pod: -</div>
    <hr style="border-color: var(--panel-border); margin: 14px 0;">
    <div class="panel-title" style="margin-bottom:10px;"><span>진행률</span></div>
    <div style="display:flex; align-items:center; gap:16px;">
      <div id="progress-ring" style="width:80px; height:80px; border-radius:50%; background:conic-gradient(var(--blue) 0%, #22252b 0); display:flex; align-items:center; justify-content:center; flex-shrink:0;">
        <div style="width:60px; height:60px; border-radius:50%; background:var(--panel-bg); display:flex; align-items:center; justify-content:center;">
          <span id="progress-ring-value" style="font-size:14px; font-weight:700;">0%</span>
        </div>
      </div>
      <div style="font-size:12px; line-height:1.9; flex:1;">
        <div>작업: <span id="progress-job-name" style="color:var(--text); font-weight:600;">-</span></div>
        <div>경과 시간: <span id="progress-elapsed" style="color:var(--text); font-weight:600;">-</span></div>
        <div>남은 프레임: <span id="progress-remaining" style="color:var(--text); font-weight:600;">-</span></div>
        <div>예상 완료: <span id="progress-eta" style="color:var(--text); font-weight:600;">-</span></div>
      </div>
    </div>
  </div>''',
'''  <div class="panel col-4 left-col-panel">
    <div class="panel-title"><span>워커 Pod 현황</span></div>
    <div class="task-grid" id="pod-fleet-grid" style="max-width:none;"></div>
    <div class="stat-label" id="cpu-usage-pods" style="margin-top:10px;">실행 중 Pod: -</div>
    <hr style="border-color: var(--panel-border); margin: 14px 0;">
    <div class="panel-title" style="margin-bottom:10px;"><span>작업 제어</span></div>
    <button id="btn-cancel" onclick="cancelCurrentJob()" style="display:none;">현재 작업 취소</button>
    <div class="stat-label" id="cancel-status" style="margin-top:8px;">실행 중인 작업 없음</div>
  </div>''')

print("all done")
