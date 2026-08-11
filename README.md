Mini Render Farm

Kubernetes(kubeadm) 기반 렌더링 작업 분산 처리 및 실시간 모니터링 시스템입니다.
사용자가 대시보드에서 단일 처리와 분산 처리를 선택해 렌더링을 실행하고, 실시간 진행률과 리소스 사용량을 확인할 수 있습니다.

핵심 결과

동일한 48프레임 장면을 워커 1대(단일)와 5대(분산)로 각각 렌더링했을 때:

모드	소요 시간
단일 처리 (워커 1대)	221s
분산 처리 (워커 5대)	12s

18.4배 속도 개선을 실측으로 확인했습니다.

렌더링 워크로드

실제 3D 렌더링 대신, 프레임마다 계산량이 크고 해상도/반복 횟수에 따라 부하를 조절할 수 있는
맨덜브로트 프랙탈 생성을 렌더링 워크로드로 사용했습니다. 각 워커 Pod는 자신에게 할당된
JOB_COMPLETION_INDEX(Kubernetes Indexed Job)를 기준으로 맡은 프레임을 계산하고, 결과 이미지를
공유 스토리지(PVC/NFS)에 저장합니다.

아키텍처 요약
사용자 → NHN Cloud LB → Ingress(NGINX) → Flask API (Deployment)
                                              │
                          ┌───────────────────┼───────────────────┐
                          ▼                    ▼                   ▼
                 Kubernetes API Server   metrics-server      SSE (진행률 스트리밍)
                          │
                          ▼
                    Indexed Job (completions / parallelism)
                          │
        ┌─────────┬─────────┬─────────┬─────────┐
        ▼         ▼         ▼         ▼         ▼
   worker-1   worker-2   worker-3   worker-4   worker-5   (맨덜브로트 렌더링 실행)
        └─────────┴─────────┴─────────┴─────────┘
                          ▼
                 PVC (NFS, ReadWriteMany)  →  ffmpeg 인코딩 → 영상 제공
작업 분산: Kubernetes Indexed Job (completions=총 프레임 수, parallelism=동시 처리 수)
자동 병렬 수 계산: 클러스터 가용 CPU를 조회해 워커 수만큼 자동으로 parallelism 결정
실시간 모니터링: SSE(Server-Sent Events)로 진행률/로그 스트리밍, metrics-server로 CPU/메모리 수집
이력 관리: SQLite (job_history 단일 테이블)
권한 관리: RBAC (네임스페이스 범위 Role + Node 조회용 ClusterRole)
배포: Helm 차트로 전체 리소스 패키징 (infra/helm)
저장소 구조
.
├── app.py, templates/, static/, Dockerfile   # Flask API 서버 소스
├── requirements.txt
├── patch_*.py                                # 개발 중 적용한 기능별 패치 기록
├── worker/
│   ├── Dockerfile                            # 워커 Pod 컨테이너 이미지
│   └── render.py                             # 맨덜브로트 렌더링 엔진 (실제 계산 로직)
├── infra/
│   ├── helm/render-farm-chart/               # 실제 배포에 쓰는 Helm 차트 (최종본)
│   ├── manifests-legacy/                     # Helm 이전에 쓰던 원본 YAML (참고용)
│   └── cluster-setup/                        # 노드 준비 스크립트, MetalLB/NFS 설정
└── docs/
    └── SETUP.md                              # 클러스터 재구축 가이드
원본 인프라 안내

이 프로젝트는 원래 NHN Cloud VM 8대(마스터 1 · 워커 5 · NFS 1 · 빌드서버 1) 위에 kubeadm으로
직접 구축했습니다. 클라우드 자체를 옮기더라도(예: AWS) 매니지드 Kubernetes가 아니라 kubeadm 기반이라
동일한 절차로 재구축할 수 있습니다. 재구축 절차와 클라우드별로 바뀌는 부분(로드밸런서, 보안그룹 등)은
docs/SETUP.md에 정리했습니다.


