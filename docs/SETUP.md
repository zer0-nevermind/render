# 클러스터 재구축 가이드

원본은 NHN Cloud VM 8대에 구축했습니다. 아래 절차를 그대로 따르면 AWS EC2 등 다른 클라우드에서도
동일하게 재구축할 수 있습니다. 클라우드별로 달라지는 부분은 각 단계에 "☁️ 클라우드별 차이"로 표시했습니다.

## 0. 인스턴스 구성 (원본 기준)

| 역할 | 대수 | 스펙 |
|---|---|---|
| Control Plane (render-master) | 1 | 4 vCPU |
| Worker (render-worker1~5) | 5 | 4 vCPU / 16GB RAM |
| NFS (render-nfs) | 1 | 2 vCPU / 8GB RAM |
| Build Server (render-build) | 1 | 2 vCPU / 8GB RAM |

OS: Ubuntu 22.04.5 LTS (전체 노드 동일)

☁️ **클라우드별 차이**: AWS라면 위 스펙에 맞는 EC2 인스턴스 타입(예: `t3.large`~`c6i.xlarge` 등)으로
대체하면 됩니다. 인스턴스 개수/역할 구성은 그대로 유지 가능합니다.

## 1. 모든 노드 공통 준비 — `infra/cluster-setup/prep-node.sh`

스왑 비활성화, 커널 모듈(`overlay`, `br_netfilter`) 로드, sysctl 네트워크 설정, CRI-O 1.33 설치,
kubeadm/kubelet/kubectl 1.33 설치까지 자동화되어 있습니다. 모든 노드(마스터+워커)에서 실행합니다.

```bash
sudo bash infra/cluster-setup/prep-node.sh
```

## 2. 컨트롤플레인 초기화 (마스터 노드)

```bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16
```

출력된 `kubeadm join ...` 명령을 각 워커 노드에서 실행해 클러스터에 합류시킵니다.

☁️ **클라우드별 차이**: `--pod-network-cidr`는 클라우드의 VPC/서브넷 CIDR과 겹치지 않게 지정해야 합니다.

## 3. CNI(Calico) 설치

원본에서 사용한 버전: **Calico v3.28.0**

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.28.0/manifests/calico.yaml
```

⚠️ **트러블슈팅 참고**: 보안그룹/방화벽에서 아래 포트를 반드시 열어야 `calico-node`가 Ready 상태가 됩니다.
- **TCP 179** (BGP, 노드 간 라우팅 정보 교환)
- **IP 프로토콜 4** (IPIP 캡슐화 트래픽, 오버레이 네트워크)

## 4. LoadBalancer — MetalLB (☁️ 클라우드별로 가장 크게 달라지는 부분)

NHN Cloud처럼 네이티브 LoadBalancer가 마땅치 않은 bare-metal성 환경에서는 **MetalLB**로
LoadBalancer IP를 직접 할당했습니다 (`infra/cluster-setup/ingress-pool.yaml`, `metallb-config.yaml`).

```bash
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml
kubectl apply -f infra/cluster-setup/ingress-pool.yaml
kubectl apply -f infra/cluster-setup/metallb-config.yaml
```

☁️ **AWS로 옮길 경우**: MetalLB가 필요 없습니다. `Service` 타입을 `LoadBalancer`로 두면 AWS가 자동으로
ALB/NLB를 프로비저닝해줍니다. `infra/helm/render-farm-chart`의 Ingress/Service 값만 그대로 두고
MetalLB 관련 리소스는 생략하면 됩니다.

## 5. 공유 스토리지 — NFS Provisioner

```bash
kubectl apply -f infra/cluster-setup/nfs-provisioner.yaml
```

NFS 서버(별도 인스턴스)를 `ReadWriteMany` PVC로 마운트해 여러 워커 Pod가 동시에 프레임 이미지를
쓸 수 있게 합니다.

☁️ **클라우드별 차이**: AWS에서는 EFS(Elastic File System)로 대체할 수 있습니다. EFS CSI 드라이버를
쓰면 별도 NFS 인스턴스 없이도 RWX 볼륨을 만들 수 있습니다.

## 6. 컨테이너 이미지 빌드 & 레지스트리

원본은 내부망 프라이빗 레지스트리(`192.168.2.75:5000`)를 사용했습니다.

```bash
docker build -t <registry>/render-api:latest .
docker push <registry>/render-api:latest
```

☁️ **클라우드별 차이**: AWS에서는 ECR(Elastic Container Registry)을 쓰거나, Docker Hub에 올려도 됩니다.
`infra/helm/render-farm-chart/values.yaml`의 `image.registry` 값만 바꿔주면 됩니다.

## 7. 애플리케이션 배포 (Helm)

```bash
helm install render-farm infra/helm/render-farm-chart
```

## 8. 보안그룹/방화벽 체크리스트

| 포트 | 용도 |
|---|---|
| 22 | SSH |
| 6443 | Kubernetes API 서버 |
| 179 (TCP) | Calico BGP |
| IP 프로토콜 4 | Calico IPIP 캡슐화 |
| 10250 | kubelet |
| 30000-32767 | NodePort 범위 |
| 80 / 443 | Ingress (HTTP/HTTPS) |
| 2049 | NFS |

## 필요 시 대체 가능한 부분 정리

| 원본(NHN Cloud) | AWS 대체 |
|---|---|
| MetalLB | ELB / NLB (네이티브 LoadBalancer Service) |
| NFS 인스턴스 | EFS + EFS CSI Driver |
| 내부 프라이빗 레지스트리 | ECR |
| Floating IP | Elastic IP |

인스턴스 자체를 클라우드 간에 그대로 옮길 수는 없지만, kubeadm 기반이라 위 절차대로 새 인스턴스에서
그대로 재현할 수 있습니다.
