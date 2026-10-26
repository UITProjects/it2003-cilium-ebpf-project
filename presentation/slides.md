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

<div class="grid grid-cols-3 gap-5">
  <div class="card neutral !p-4" v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600, delay: 200 } }">
    <div class="agenda-n">1</div>
    <div class="agenda-t">Giới thiệu Kubernetes networking</div>
    <ul class="agenda-l">
      <li>Linux namespace & veth</li>
      <li>Mô hình mạng Kubernetes</li>
      <li>CNI nối Pod vào mạng</li>
    </ul>
  </div>
  <div class="card split !p-4" v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600, delay: 400 } }">
    <div class="agenda-n">2</div>
    <div class="agenda-t">Cơ chế cốt lõi: iptables vs eBPF</div>
    <ul class="agenda-l">
      <li>Netfilter / iptables · eBPF & BPF map</li>
      <li>Đường đi packet · Service load balancing</li>
      <li>NetworkPolicy</li>
    </ul>
    <div class="tiny muted mt-2">Hiện thực: Calico · Cilium</div>
  </div>
  <div class="card neutral !p-4" v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600, delay: 600 } }">
    <div class="agenda-n">3</div>
    <div class="agenda-t">Thực nghiệm kiểm chứng: Calico vs Cilium</div>
    <ul class="agenda-l">
      <li><b>E1</b> Hiệu năng Service theo quy mô</li>
      <li><b>E2</b> NetworkPolicy</li>
      <li><b>E3</b> Runtime security</li>
    </ul>
  </div>
</div>


---
layout: section
transition: slide-up | slide-down
---

# 1. Giới thiệu Kubernetes networking

<div class="text-xl muted mt-4">Từ Linux namespace đến Pod</div>

---

# 1.1 Linux namespace & network namespace

<NetnsIntro />

<!--
Namespace: cơ chế của kernel cô lập một loại tài nguyên cho một nhóm process (container = process + namespace). Kubernetes không tạo "máy ảo" mạng, chỉ dùng network namespace.
→ Kubernetes: mỗi Pod = 1 netns riêng: interface, route, iptables, conntrack, cổng riêng; container trong Pod dùng chung netns do pause container giữ · ip netns, lsns -t net
-->

---

# 1.2 veth: cáp mạng ảo nối hai namespace

<VethPair />

<!--
veth = cặp interface ảo: packet vào đầu này ra đầu kia. CNI tạo cặp khi Pod khởi động: một đầu vào netns của Pod (eth0), đầu kia ở host.
Là lối ra duy nhất của Pod → mọi packet đi vào network stack của host; datapath chạy ở đó do CNI thiết lập (các slide sau).
-->

---

# 1.3 Mô hình mạng Kubernetes

<K8sModel />

<!--
Ba yêu cầu của mô hình mạng Kubernetes:
① Pod ↔ Pod mọi node, không NAT
② Node ↔ mọi Pod trên node
③ IP Pod tự thấy = IP người khác thấy
Service: ClusterIP ảo không gắn interface, chỉ là rule DNAT trên mỗi node (kube-proxy / eBPF).
-->

---

# 1.4 Primitive mạng của Linux & CNI

<LinuxPrimitives />

<div class="small muted text-center mt-2">

*netns · pause container · veth · CNI: chi tiết từng thành phần xem trong báo cáo*

</div>

---
layout: section
transition: slide-up | slide-down
---

# 2. Cơ chế cốt lõi: iptables vs eBPF

<div class="text-xl muted mt-4">Hiện thực: Calico · Cilium</div>

---

# 2.1 iptables: rule, chain & conntrack

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

# 2.2 eBPF: máy ảo an toàn trong kernel Linux

<EbpfVM />

<!--
Các hook eBPF:
- XDP: trong driver NIC, trước sk_buff, sớm nhất (LB North-South)
- TC ingress/egress: mọi interface kể cả veth → Cilium dùng cho routing, NAT, policy
- cgroup/socket (connect4, sendmsg4): dịch địa chỉ Service ngay tại connect()
- sock_ops / sk_msg (sockmap): nối thẳng 2 socket cùng host
- kprobe, tracepoint, LSM: observability & bảo mật runtime (Tetragon)
-->

---

# 2.3 BPF map & datapath của Cilium

Trước khi có packet: agent ghi sẵn bảng tra cứu

<BpfMaps />

<!--
Chương trình eBPF không giữ trạng thái; trạng thái nằm trong BPF map (key-value trong kernel), read/write từ cả eBPF và user space.
Loại map: hash, LRU hash (conntrack), array, LPM trie (CIDR trong ipcache), per-CPU, ring buffer / perf (đẩy sự kiện cho Hubble).
Kích thước map cố định khi tạo → phải định cỡ theo quy mô cụm.

Backup (đã bỏ khỏi slide):
- Service LB: cilium_lb4_services_v2 / backends_v3 map Service IP → Pod backend, thay kube-proxy (dùng trong E1, không dùng ở 2.4).
- eBPF program còn gắn ở eth0 (NIC, traffic từ ngoài node) và cilium_host (traffic của host), không chỉ lxc*.
- Tên map tùy phiên bản Cilium; xem cilium-dbg map list. Identity trên slide là ví dụ.
-->

---

# 2.4 Đường đi packet: intra-node

<PathCompare />

<!--
Intra-pod: các container chung netns → chung IP & không gian cổng, nói chuyện qua localhost (vẫn qua toàn bộ TCP/IP stack; sockmap có thể bỏ qua).
Intra-node: iptables đi qua bridge/route /32, toàn bộ Netfilter của host; Cilium redirect thẳng sang veth Pod đích (BPF host routing, kernel ≥ 5.10).
-->

---

# 2.5 Đường đi packet: inter-node (direct routing)

<DirectRouting />

<!--
Backup – route giữa các node được cài thế nào:
- Calico: BIRD quảng bá podCIDR của node qua BGP.
- Cilium: autoDirectNodeRoutes cài route trực tiếp (các node cùng L2).
-->

---

# 2.6 Load balancing Service: kube-proxy iptables

```text {1|2-3|4-5}
-A KUBE-SERVICES -d 10.233.12.34/32 -p tcp --dport 80 -j KUBE-SVC-ABCD
-A KUBE-SVC-ABCD -m statistic --mode random --probability 0.5 -j KUBE-SEP-1111
-A KUBE-SVC-ABCD -j KUBE-SEP-2222
-A KUBE-SEP-1111 -p tcp -j DNAT --to-destination 10.244.1.20:8080
-A KUBE-SEP-2222 -p tcp -j DNAT --to-destination 10.244.2.21:8080
```

<div class="cmp small mt-3">
<div v-click>

- `KUBE-SERVICES`: **1 rule / (ClusterIP, port)**, gọi từ `PREROUTING` & `OUTPUT`
- `KUBE-SVC-*`: chọn backend ngẫu nhiên (`statistic`, 1/n, 1/(n-1)…)
- `KUBE-SEP-*`: **DNAT** tới Pod backend

</div>
<div v-click>

- **Tra cứu $O(n)$**: SYN có thể duyệt hàng nghìn rule → lộ rõ với TCP_CRR
- **Cập nhật**: `iptables-restore` giữ khoá xtables, chậm theo kích thước table (partial sync từ 1.27)
- **conntrack** chung: tranh chấp khoá, giới hạn `nf_conntrack_max`

</div>
</div>

---

# 2.7 NetworkPolicy: iptables vs eBPF

<PolicyTranslate />

<!--
Packet chỉ mang IP, không mang label → mọi hiện thực đều phải dịch label → thứ kiểm tra được trên packet.
iptables: policy gắn với IP tạm thời → Pod tạo/huỷ ⇒ Felix trên mọi node sửa ipset; trong lúc trễ: chặn nhầm Pod mới / cho phép nhầm IP tái sử dụng.
eBPF: Pod mới cùng label ⇒ identity đã có, policy map giữ nguyên, chỉ phân phối ipcache (hoặc identity đi trong VNI). Hỗ trợ L7 qua Envoy (CiliumNetworkPolicy).
-->

---
layout: section
transition: slide-up | slide-down
---

# 3. Thực nghiệm kiểm chứng: Calico vs Cilium

---
clicks: 5
---

# 3.1 Topology homelab

<div class="tiny muted -mt-3 mb-1">Terraform (bpg/proxmox) · Ansible · Kubespray · Cilium bằng Helm. Hai cụm 3 node song song, VM giống hệt nhau (4 vCPU, 4 GiB, 120 GB, Ubuntu 24.04, kernel 6.8).</div>

<Topology />

---

# 3.2 E1 · Thiết lập đo

<div class="text-center mb-4">

<span class="hl">**N** = số Service trong cụm, biến duy nhất thay đổi giữa các lần đo</span>

</div>

<div class="cmp small">
<div>

### Tải nền
- Tạo $N \in \{100;\ 2080;\ 4060;\ 6040;\ 8020;\ 10000\}$ Service giả
- Mỗi Service → 3 Pod `pause` → ~**11 rule nat** (iptables) / ~**5 dòng** LB map (Cilium)

</div>
<div v-click>

### Đo
- **fortio 1.75.3**, client & server trên 2 worker khác nhau, gọi **ClusterIP** với `-keepalive=false` (mỗi request 1 connection TCP mới)
- 200 req/s · 4 connection · 30 s · warm-up 5 s
- Chờ EndpointSlice + số rule ổn định + 20 s rồi mới đo
- 3 lần / N → **36 lần chạy**, kích thước table đọc trên node client (`iptables-save -t nat`, `cilium-dbg bpf lb list`)
- Tải nền giống nhau trên 2 cụm (Prometheus, Loki, Alloy, metrics-server); Tetragon tạm dừng khi đo

</div>
</div>

---

# 3.3 E1 · Kết quả

<img src="/e1-hero.png" class="mx-auto" style="max-height:335px" v-motion :initial="{ y: 40, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600 } }" />

<div v-click>

| N Service | Table iptables | Table Cilium | p50 iptables (ms) | p50 Cilium (ms) | p99 ipt / cil (ms) | p50 ipt/cil |
|---:|---:|---:|---:|---:|---:|---:|
| 100 | 1 303 | 664 | 2.33 | 2.48 | 4.28 / 6.59 | 0.94 |
| 4 060 | 44 863 | 20 464 | 3.31 | 2.36 | 6.08 / 5.03 | 1.40 |
| 10 000 | 110 203 | 50 164 | **4.93** | **2.37** | 9.93 / 4.96 | 2.08 |

</div>

---

# 3.4 E1 · Toàn bộ phân phối độ trễ

<img src="/e1-cdf.png" class="w-full" v-motion :initial="{ y: 40, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600 } }" />

---

# 3.5 E2 · Phân đoạn mạng: chặn lateral movement

<PolicySegment />

<div class="small mt-2">
<v-clicks>

- **Default deny** cả ingress lẫn egress → chỉ đường tới Redis **qua Cart**, tới Payment **qua Checkout**; lối tắt trực tiếp bị từ chối
- Frontend bị chiếm quyền chỉ chạm được allowlist → **thu hẹp blast radius**; nhận diện theo <span class="hl">**security identity**</span> (label), không theo IP

</v-clicks>
</div>

---

# 3.6 E3 · Tetragon là gì?

<div class="small mb-2">

**Tetragon** = engine **observability & thực thi bảo mật runtime** dựa trên **eBPF** (một phần của Cilium), nhìn ở tầng **syscall · process · file** — khác với NetworkPolicy (chỉ ở tầng mạng).

</div>

<div class="cmp small">
<div class="card ebpf">

### Gắn vào kernel (eBPF)
Hook `kprobe · tracepoint · LSM` → thấy:
- **syscall**, exec/exit **process**
- **read/write file**, mạng, credential

</div>
<div class="card ebpf" v-click>

### Xử lý
- Lọc **ngay trong kernel** theo `TracingPolicy` → chi phí thấp
- Gắn **ngữ cảnh K8s**: pod, namespace, label, binary
- **Observe** + tùy chọn **enforce** (`SIGKILL`, `Override -EPERM`)

</div>
</div>

<div class="small mt-3" v-click>

Trong E3, Tetragon theo dõi hook <span class="hl">`security_file_permission`</span> để bắt việc đọc `serviceaccount/token` — thứ File Inclusion làm **ngay trong PHP worker**. <span class="muted">(Cần kernel có eBPF/BTF; BPF-LSM để enforce.)</span>

</div>

---

# 3.7 E3 · Vì sao iptables không làm được

<div class="cmp small mt-2">
<div class="card ipt">

### iptables / Calico
- Chỉ thấy **packet ở hook mạng** (L3/L4): IP, port, proto
- **Không** thấy process, syscall hay thao tác đọc file
- Là **firewall**, không phải bảo mật runtime
- Muốn observe process/file → phải thêm công cụ khác (`auditd`…), nằm ngoài iptables

</div>
<div class="card ebpf" v-click>

### Tetragon / eBPF
- Thấy **syscall · process · file · mạng** + **ngữ cảnh K8s**
- **Lọc & chặn ngay trong kernel**, không cần sidecar
- Một `TracingPolicy` áp cho đúng Pod/đường dẫn file

</div>
</div>

<div class="mt-5 text-center" v-click>

<span class="hl">**Tetragon đòi hỏi eBPF** (kprobe/LSM, BTF)</span> — datapath **iptables thuần không cung cấp** instrumentation này.<br/>
→ Demo E3 chỉ chạy được trên cụm **Cilium/eBPF**; phía iptables **không có công cụ tương đương**.

</div>

---

# 3.8 E3 · Sau khai thác: đọc ServiceAccount token

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
---

<img src="/logo-uit.jpg" class="h-16 mx-auto mb-6" />

<h1 v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 700 } }" style="font-size:2.6rem;color:#14532d">Cảm ơn!</h1>

<div v-motion :initial="{ y: 30, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 700, delay: 250 } }" class="text-2xl mt-2">Hỏi & Đáp</div>

<div v-motion :initial="{ opacity: 0 }" :enter="{ opacity: 1, transition: { duration: 700, delay: 550 } }" class="text-sm muted mt-8">
Nhóm 12 · IT2003.11.CH · Cilium and eBPF-based Networking for Kubernetes
</div>
