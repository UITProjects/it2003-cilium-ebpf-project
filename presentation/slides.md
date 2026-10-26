---
theme: default
title: Cilium & eBPF vs iptables trong Kubernetes
info: |
  IT2003.11.CH – Công nghệ Mạng và Truyền thông hiện đại – Nhóm 12.
  Slides rút gọn từ báo cáo docs-latex.
colorSchema: light
aspectRatio: 16/9
canvasWidth: 980
fonts:
  sans: Be Vietnam Pro
  mono: JetBrains Mono
transition: slide-left | slide-right
drawings:
  persist: false
layout: cover
class: text-left
background: '#f7faf7'
---

<div class="flex items-center gap-4 mb-6">
  <img src="/logo-uit.jpg" class="h-16" />
  <div class="text-sm leading-tight muted">
    ĐẠI HỌC QUỐC GIA TP.HCM<br/>TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN
  </div>
</div>

<h1 v-motion :initial="{ x: -60, opacity: 0 }" :enter="{ x: 0, opacity: 1, transition: { duration: 700 } }" style="font-size:2.1rem;line-height:1.2;color:#14532d">Cilium and eBPF-based Networking for Kubernetes</h1>

<div v-motion :initial="{ x: -60, opacity: 0 }" :enter="{ x: 0, opacity: 1, transition: { duration: 700, delay: 250 } }" class="text-xl mt-1 mb-6">A Modern Alternative to Traditional iptables Networking</div>

<div v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 700, delay: 550 } }" class="grid grid-cols-2 gap-6 text-sm">
<div>

**Môn học:** Công nghệ Mạng và Truyền thông hiện đại<br/>
**Mã lớp:** IT2003.11.CH · **PGS.** Lê Trung Quân<br/>
Học kì II, 2025–2026

</div>
<div>

**Nhóm 12**<br/>
250202052 – Nguyễn Hoài Phương<br/>
250202060 – Nguyễn Long Vũ<br/>
26848033 – Ngô Vũ Minh Đạt

</div>
</div>

---

# Agenda

<div class="text-center mt-1 mb-6" v-motion :initial="{ opacity: 0 }" :enter="{ opacity: 1, transition: { duration: 600 } }">
  <span class="hl">Mục tiêu: so sánh <b>iptables</b> phổ biến nhất với <b>eBPF</b> hiện đại ở quy mô cloud-native lớn</span>
</div>

<div class="grid grid-cols-2 gap-6">
  <div class="card neutral !p-4" v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600, delay: 200 } }">
    <div class="agenda-n">1</div>
    <div class="agenda-t">Nền tảng: Kubernetes networking, iptables & eBPF</div>
    <ul class="agenda-l">
      <li>netns · veth · CNI · mô hình mạng Kubernetes</li>
      <li>iptables (Netfilter) · eBPF & BPF map</li>
      <li>Đường đi packet · direct routing</li>
    </ul>
  </div>
  <div class="card split !p-4" v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600, delay: 400 } }">
    <div class="agenda-n">2</div>
    <div class="agenda-t">Thực nghiệm: Calico vs Cilium</div>
    <ul class="agenda-l">
      <li><b>E1</b> Service load balancing theo quy mô <span class="muted">· cơ chế → kết quả</span></li>
      <li><b>E2</b> NetworkPolicy <span class="muted">· cơ chế → demo</span></li>
      <li><b>E3</b> Runtime security <span class="muted">· cơ chế → demo</span></li>
    </ul>
  </div>
</div>

---

# 1.1 Linux primitive & CNI: netns · veth

<LinuxPrimitives />

<!--
Namespace: cơ chế của kernel cô lập một loại tài nguyên cho một nhóm process (container = process + namespace). Kubernetes không tạo "máy ảo" mạng, chỉ dùng network namespace.
→ Mỗi Pod = 1 netns riêng: interface, route, iptables, conntrack, cổng riêng; container trong Pod dùng chung netns do pause container giữ · ip netns, lsns -t net
veth = cặp interface ảo: packet vào đầu này ra đầu kia. CNI tạo cặp khi Pod khởi động: một đầu vào netns của Pod (eth0), đầu kia ở host.
Là lối ra duy nhất của Pod → mọi packet đi vào network stack của host; datapath chạy ở đó do CNI thiết lập (các slide sau).
Chi tiết từng thành phần xem trong báo cáo.
-->

---

# 1.2 Mô hình mạng Kubernetes & direct routing

<K8sModel />

<!--
Ba yêu cầu của mô hình mạng Kubernetes:
① Pod ↔ Pod mọi node, không NAT
② Node ↔ mọi Pod trên node
③ IP Pod tự thấy = IP người khác thấy
Inter-node (click ②): mỗi node có route tới podCIDR của node kia qua IP node đó → packet giữ nguyên IP Pod trên L2 network.
Service: ClusterIP ảo không gắn interface, chỉ là rule DNAT trên mỗi node (kube-proxy / eBPF) → E1.

Backup – route giữa các node được cài thế nào:
- Calico: BIRD quảng bá podCIDR của node qua BGP.
- Cilium: autoDirectNodeRoutes cài route trực tiếp (các node cùng L2).
- Direct routing: không encapsulation (không VXLAN/Geneve header) → MTU 1500 đầy đủ cho Pod.
- Cả hai cụm cùng direct routing → khác biệt trong thực nghiệm chỉ đến từ xử lý Service / policy.
-->

---

# 1.3 iptables: rule, chain & conntrack

<IptablesChain />

<!--
Rule tổ chức thành table (filter, nat, mangle, raw) và chain. Mỗi chain là danh sách duyệt tuần tự đến target kết thúc (ACCEPT, DROP, DNAT…).
conntrack: chỉ packet đầu tiên duyệt table nat; quyết định NAT được lưu cho các packet sau.
→ Chi phí iptables tập trung ở thiết lập connection → E1 đo connection mới cho mỗi request.

Backup – Netfilter (nếu được hỏi):
- iptables chỉ là công cụ ghi rule; rule chạy trong Netfilter, framework hook của kernel.
- 5 hook: PREROUTING (vừa vào) → routing decision → INPUT (cho process local) hoặc FORWARD (đi qua node, vd. sang Pod) → OUTPUT (process local gửi ra) → POSTROUTING (trước khi rời interface).
- kube-proxy gắn KUBE-SERVICES vào table nat ở PREROUTING (traffic từ Pod/ngoài vào) và OUTPUT (traffic từ chính node); SNAT/masquerade ở POSTROUTING.
-->

---

# 1.4 eBPF: máy ảo an toàn trong kernel Linux

<EbpfVM />

<!--
Chương trình được load một lần (verifier kiểm tra an toàn, JIT ra mã máy), rồi gắn vào một kernel hook.
Hook mạng mà Cilium datapath dùng (E1/E2):
- TC ingress/egress: mọi interface kể cả veth → routing, NAT, policy
- cgroup/socket (connect4, sendmsg4): dịch địa chỉ Service ngay tại connect()
- sock_ops / sk_msg (sockmap): nối thẳng 2 socket cùng host
Hook file/process (kprobe, tracepoint, LSM) → Tetragon, xem E3 (2.3.1).
Backup: còn uprobe (hàm user space), fentry/fexit, perf_event (profiling).
-->

---

# 1.5 BPF map & datapath của Cilium

Trước khi có packet: agent ghi sẵn bảng tra cứu

<BpfMaps />

<!--
Chương trình eBPF không giữ trạng thái; trạng thái nằm trong BPF map (key-value trong kernel), read/write từ cả eBPF và user space.
Loại map: hash, LRU hash (conntrack), array, LPM trie (CIDR trong ipcache), per-CPU, ring buffer / perf (đẩy sự kiện cho Hubble).
Kích thước map cố định khi tạo → phải định cỡ theo quy mô cụm.

Backup (đã bỏ khỏi slide):
- Service LB: cilium_lb4_services_v2 / backends_v3 map Service IP → Pod backend, thay kube-proxy (xem E1, 2.1.1).
- eBPF program còn gắn ở eth0 (NIC, traffic từ ngoài node) và cilium_host (traffic của host), không chỉ lxc*.
- Tên map tùy phiên bản Cilium; xem cilium-dbg map list. Identity trên slide là ví dụ.
-->

---

# 1.6 Đường đi packet: intra-node

<PathCompare />

<!--
Intra-pod: các container chung netns → chung IP & không gian cổng, nói chuyện qua localhost (vẫn qua toàn bộ TCP/IP stack; sockmap có thể bỏ qua).
Intra-node: iptables đi qua bridge/route /32, toàn bộ Netfilter của host; Cilium redirect thẳng sang veth Pod đích (BPF host routing, kernel ≥ 5.10).
-->

---
clicks: 5
transition: slide-up | slide-down
---

# 2. Thực nghiệm · Topology homelab

<div class="tiny muted -mt-3 mb-1">Terraform (bpg/proxmox) · Ansible · Kubespray · Cilium bằng Helm. Hai cụm 3 node song song, VM giống hệt nhau (4 vCPU, 4 GiB, 120 GB, Ubuntu 24.04, kernel 6.8).</div>

<Topology />

---

# 2.1.1 E1 · Service load balancing: O(n) vs hash

<div class="text-center mb-8">

<span class="hl">**N** = số Service trong cụm, biến duy nhất thay đổi giữa các lần đo</span>

</div>

<LookupCompare />

<!--
Giả thuyết: iptables duyệt KUBE-SERVICES tuần tự → độ trễ connection mới tăng theo N; Cilium tra hash map → không đổi.

Thiết lập đo:
- Tải nền: N ∈ {100; 2080; 4060; 6040; 8020; 10000} Service giả, mỗi Service → 3 Pod pause → ~11 rule nat (iptables) / ~5 dòng LB map (Cilium).
- fortio 1.75.3, client & server trên 2 worker khác nhau, gọi ClusterIP với -keepalive=false (mỗi request 1 connection TCP mới).
- 200 req/s · 4 connection · 30 s · warm-up 5 s; chờ EndpointSlice + số rule ổn định + 20 s rồi mới đo.
- 3 lần / N → 36 lần chạy; kích thước table đọc trên node client (iptables-save -t nat, cilium-dbg bpf lb list).
- Tải nền giống nhau trên 2 cụm (Prometheus, Loki, Alloy, metrics-server); Tetragon tạm dừng khi đo.
- p50 = latency trung vị của 1 connection mới; p99 = đuôi chậm; mỗi N lấy trung bình 3 lần.

Backup – kube-proxy iptables cho 1 Service:
-A KUBE-SERVICES -d 10.233.12.34/32 -p tcp --dport 80 -j KUBE-SVC-ABCD      (1 rule / (ClusterIP, port), gọi từ PREROUTING & OUTPUT)
-A KUBE-SVC-ABCD -m statistic --mode random --probability 0.5 -j KUBE-SEP-1111   (chọn backend ngẫu nhiên)
-A KUBE-SEP-1111 -p tcp -j DNAT --to-destination 10.244.1.20:8080           (DNAT tới Pod backend)
Cập nhật: iptables-restore giữ khoá xtables, chậm theo kích thước table.
-->

---

# 2.1.2 E1 · Kết quả

<img src="/e1-hero.png" class="mx-auto" style="max-height:335px" v-motion :initial="{ y: 40, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600 } }" />

<div v-click>

| N Service | Table iptables | Table Cilium | p50 iptables (ms) | p50 Cilium (ms) | p99 ipt / cil (ms) | p50 ipt/cil |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 1 303 | 664 | 2.33 | 2.48 | 4.28 / 6.59 | 0.94 |
| 4 060 | 44 863 | 20 464 | 3.31 | 2.36 | 6.08 / 5.03 | 1.40 |
| 10 000 | 110 203 | 50 164 | **4.93** | **2.37** | 9.93 / 4.96 | 2.08 |

</div>

---

# 2.1.3 E1 · Toàn bộ phân phối độ trễ

<img src="/e1-cdf.png" class="w-full" v-motion :initial="{ y: 40, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600 } }" />

---

# 2.2.1 E2 · NetworkPolicy: IP vs identity

<PolicyTranslate />

<!--
Packet chỉ mang IP, không mang label → mọi hiện thực đều phải dịch label → thứ kiểm tra được trên packet.
iptables: policy gắn với IP tạm thời → Pod tạo/huỷ ⇒ Felix trên mọi node sửa ipset; trong lúc trễ: chặn nhầm Pod mới / cho phép nhầm IP tái sử dụng.
eBPF: Pod mới cùng label ⇒ identity đã có, policy map giữ nguyên, chỉ phân phối ipcache (hoặc identity đi trong VNI). Hỗ trợ L7 qua Envoy (CiliumNetworkPolicy).
-->

---

# 2.2.2 E2 · Phân đoạn mạng: chặn lateral movement

<PolicySegment />

<div class="small mt-2">
<v-clicks>

- **Default deny** cả ingress lẫn egress → chỉ đường tới Redis **qua Cart**, tới Payment **qua Checkout**; lối tắt trực tiếp bị từ chối
- Frontend bị chiếm quyền chỉ chạm được allowlist → **thu hẹp blast radius**; nhận diện theo <span class="hl">**security identity**</span> (label), không theo IP

</v-clicks>
</div>

---
layout: center
class: text-center
transition: fade
---

<span class="demo-badge" v-motion :initial="{ scale: 0.4, opacity: 0 }" :enter="{ scale: 1, opacity: 1, transition: { type: 'spring', stiffness: 260, damping: 14 } }">LIVE DEMO</span>

# 2.2.3 E2 · Demo: chặn lateral movement & reverse shell

<div class="text-left inline-block small mt-4">

```bash
# Nền: default-deny + least-privilege cho Online Boutique (Cilium)
kubectl apply -f e2/cilium/        # 15 CiliumNetworkPolicy · ns microservices-google-demo

# Mô phỏng frontend bị chiếm quyền (ephemeral container trong Pod frontend)
kubectl debug -it pod/<frontend> -n microservices-google-demo \
  --image=nicolaka/netshoot --target=server -- bash
nc -zv -w3 cartservice 7070        # flow hợp lệ   → succeeded
nc -zv -w3 redis-cart 6379         # lateral move   → BLOCK (timeout)
nc -zv -w3 paymentservice 50051    # bỏ qua Checkout → BLOCK (timeout)
hubble observe -n microservices-google-demo --verdict DROPPED   # "Policy denied", ai → ai

# Cơ chế trong kernel: Calico ipset vs Cilium identity
ipset list | grep -A3 cali40s      # Calico: label → tập IP
cilium identity list               # Cilium: label → identity số

# Bridge → E3: chặn callback reverse shell từ DVWA
kubectl apply -f e2/case_reverse_shell.yaml   # egress chỉ web/DNS/ping; chặn TCP 4444
```

<div class="tiny muted mt-1">Timeout đơn thuần chưa đủ — đối chiếu flow <code>Policy denied</code> trong Hubble.</div>

</div>

---

# 2.3.1 E3 · Tetragon: eBPF hook ở tầng process/file

<EbpfHooks />

<!--
Tetragon = engine observability & thực thi bảo mật runtime dựa trên eBPF (một phần của Cilium), nhìn ở tầng syscall · process · file — khác với NetworkPolicy (chỉ ở tầng mạng).
- Gắn vào kernel: kprobe · tracepoint · LSM → thấy syscall, exec/exit process, read/write file, mạng, credential.
- Lọc ngay trong kernel theo TracingPolicy → chi phí thấp; gắn ngữ cảnh K8s (pod, namespace, label, binary).
- Observe + tùy chọn enforce (SIGKILL, Override -EPERM).

Vì sao iptables không làm được:
- iptables/Calico chỉ thấy packet ở hook mạng (L3/L4: IP, port, proto); không thấy process, syscall hay thao tác đọc file. Là firewall, không phải bảo mật runtime.
- Muốn observe process/file → phải thêm công cụ khác (auditd…), nằm ngoài iptables.
→ Tetragon đòi hỏi eBPF (kprobe/LSM, BTF); demo E3 chỉ chạy trên cụm Cilium/eBPF, phía iptables không có công cụ tương đương.

Trong E3, Tetragon theo dõi hook security_file_permission để bắt việc đọc serviceaccount/token — thứ File Inclusion làm ngay trong PHP worker. (Cần kernel có eBPF/BTF; BPF-LSM để enforce.)
-->

---

# 2.3.2 E3 · Sau khai thác: đọc ServiceAccount token

<TetragonFlow />

<div class="small mt-2">
<v-clicks>

- **Command Injection** sinh process mới → giám sát theo **exec** bắt được ngay
- **File Inclusion** đọc token **ngay trong PHP worker** có sẵn → giám sát theo process **bỏ sót** → cần rule theo **đường dẫn file**, không theo tên process
- Policy hiện tại ở chế độ <span class="hl">**monitor-only**</span>: ghi nhận, chưa chặn (enforce `Override -EPERM` là tuỳ chọn, cần kernel hỗ trợ)

</v-clicks>
</div>

---
layout: center
class: text-center
transition: fade
---

<span class="demo-badge" v-motion :initial="{ scale: 0.4, opacity: 0 }" :enter="{ scale: 1, opacity: 1, transition: { type: 'spring', stiffness: 260, damping: 14 } }">LIVE DEMO</span>

# 2.3.3 E3 · Demo: Tetragon bắt hành vi sau khai thác

<div class="text-left inline-block small mt-4">

```bash
# 1. Upload PoC qua trang File Upload của DVWA → hackable/uploads/expoilt.php
# 2. Kích hoạt qua File Inclusion (LFI): ?page=../../hackable/uploads/expoilt.php
#    → đọc token NGAY trong PHP worker, không sinh process mới

# 3. Rule giám sát đọc file token (hook security_file_permission)
kubectl apply -f e3/Tetragon/dvwa-token-monitor.yaml
kubectl exec -n kube-system ds/tetragon -c tetragon -- \
  tetra getevents -o compact        # sự kiện đọc .../serviceaccount/token
```

**PoC** `expoilt.php`: đọc token → kiểm tra danh tính & quyền Kubernetes API

</div>

---
layout: center
class: text-center
---

<img src="/logo-uit.jpg" class="h-16 mx-auto mb-6" />

<h1 v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 700 } }" style="font-size:2.6rem;color:#14532d">Cảm ơn!</h1>

<div v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 700, delay: 250 } }" class="text-2xl mt-2">Hỏi & Đáp</div>

<div v-motion :initial="{ opacity: 0 }" :enter="{ opacity: 1, transition: { duration: 700, delay: 550 } }" class="text-sm muted mt-8">
Nhóm 12 · IT2003.11.CH · Cilium and eBPF-based Networking for Kubernetes
</div>
