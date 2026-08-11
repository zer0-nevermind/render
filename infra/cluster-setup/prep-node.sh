#!/bin/bash
set -e

# 스왑 비활성화 (쿠버네티스 필수 조건)
sudo swapoff -a
sudo sed -i '/ swap / s/^/#/' /etc/fstab

# 커널 모듈 로드
cat <<EOM | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOM
sudo modprobe overlay
sudo modprobe br_netfilter

# 네트워크 sysctl 설정
cat <<EOM | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOM
sudo sysctl --system

# cri-o 설치 (버전 1.33)
sudo apt-get update
sudo apt-get install -y software-properties-common curl gpg
curl -fsSL https://pkgs.k8s.io/addons:/cri-o:/prerelease:/main/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/cri-o-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/cri-o-apt-keyring.gpg] https://pkgs.k8s.io/addons:/cri-o:/prerelease:/main/deb/ /" | sudo tee /etc/apt/sources.list.d/cri-o.list
sudo apt-get update
sudo apt-get install -y cri-o
sudo systemctl enable --now crio

# kubeadm/kubelet/kubectl 설치 (v1.33)
curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /" | sudo tee /etc/apt/sources.list.d/kubernetes.list
sudo apt-get update
sudo apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
sudo systemctl enable kubelet

echo "=== 완료: $(hostname) ==="
