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

# 1.3 Calico · iptables: rule, chain & conntrack

<IptablesChain />

<!--
Người trình bày: phụ trách Calico. Phạm vi là Calico dùng Linux datapath iptables trong thực nghiệm này; Calico còn có chế độ eBPF.
Giải thích rule, table và chain trước, sau đó conntrack. Chỉ packet đầu tiên của kết nối đi qua xử lý NAT; trạng thái NAT được áp dụng cho các packet sau.
E1 đo kết nối mới, vì vậy cần phân biệt chi phí thiết lập kết nối với xử lý packet của kết nối đã có.
Chuyển tiếp: xem các thành phần này xuất hiện ở đâu trên đường Pod tới Pod cùng node.
-->

---

# 1.4 Calico · Đường đi packet giữa hai Pod cùng node

<PathCompare mode="calico" />

<div class="small mt-3">

- Packet rời Pod A qua **veth**, đi vào network stack của host.
- Host định tuyến tới Pod B; traffic đi qua các hook **Netfilter**, nơi rule iptables thực hiện kiểm tra tương ứng.
- Ví dụ này dùng **IP Pod trực tiếp**; không minh họa bước dịch ClusterIP của Service.

</div>

<!--
Người trình bày: phụ trách Calico. Sơ đồ khái quát, không phải mọi hook đều thực hiện NAT cho mọi packet. Conntrack lưu trạng thái; đường đi thực tế phụ thuộc cấu hình datapath.
Kết thúc phần Calico: phần vừa rồi là đường xử lý của cụm Calico dùng iptables. Mời phần Cilium để giải thích chương trình eBPF và BPF map trước khi xem đường đi packet tương ứng.
-->

---

# 1.5 Cilium · Chương trình eBPF & BPF map

<EbpfIntro />

<!--
Người trình bày: phụ trách Cilium. Chương trình được biên dịch thành BPF bytecode trước khi nạp qua bpf(); verifier kiểm tra và JIT biên dịch thành mã máy khi được hỗ trợ/bật.
Chương trình gắn vào hook và sử dụng BPF maps trong kernel. cilium-agent cập nhật thông tin endpoint, identity và policy; chương trình datapath cũng có thể cập nhật trạng thái như conntrack.
Các dòng trong bảng mô tả chức năng, không khẳng định mọi map đều có cùng cấu trúc hay độ phức tạp O(1).
Chuyển tiếp: xem chương trình eBPF và các map tham gia xử lý packet Pod tới Pod cùng node.
-->

---

# 1.6 Cilium · Đường đi packet giữa hai Pod cùng node

<PathCompare mode="cilium" />

<div class="small mt-3">

- Packet từ Pod A đi vào chương trình **eBPF** ở phía host của veth.
- Datapath sử dụng trạng thái kết nối, identity, policy và endpoint để quyết định xử lý; hình mô tả các chức năng chính.
- Với **BPF host routing** được bật và hỗ trợ, packet được chuyển tiếp tới Pod cục bộ mà không đi theo đường Netfilter như hình Calico.

</div>

<!--
Người trình bày: phụ trách Cilium. Ví dụ dùng IP Pod trực tiếp, không phải đường Service load balancing. Các IP và identity chỉ là minh họa.
Không coi các ô trong hình là thứ tự hook cố định cho mọi trường hợp; policy có thể được thực thi ở phía endpoint nguồn và đích tùy hướng traffic/cấu hình.
Không suy ra kết quả hiệu năng từ hình. E1 trình bày phép đo Service ở phần thực nghiệm.
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

# 2.2.2 E2 · Phân đoạn mạng để hạn chế lateral movement

<div class="text-sm muted -mt-2 mb-3">Giả định frontend đã bị chiếm quyền: kiểm thử kết nối từ Pod này tới các dịch vụ trong và ngoài allowlist.</div>

<PolicySegment />

<div class="small mt-2">
<v-clicks>

- **Default deny** cả ingress lẫn egress → chỉ đường tới Redis **qua Cart**, tới Payment **qua Checkout**; lối tắt trực tiếp bị từ chối
- Giới hạn kết nối ngoài allowlist để **thu hẹp phạm vi ảnh hưởng**; kiểm thử TCP không chứng minh đã ngăn mọi hình thức lateral movement

</v-clicks>
</div>

---

# 2.2.3 E2 · Kiểm chứng NetworkPolicy bằng Hubble

<div class="text-lg mb-5">Policy quy định đường được phép; <b class="text-green-800">Hubble quan sát traffic và lý do bị drop.</b></div>

<table class="w-full text-sm !mb-5">
<thead><tr><th>Luồng kiểm thử</th><th>Kết quả kỳ vọng</th><th>Ý nghĩa quan sát</th></tr></thead>
<tbody>
<tr><td><b>frontend → cartservice</b><br>TCP / 7070</td><td class="text-green-700"><b>FORWARDED</b></td><td>Packet được chuyển tiếp tại điểm quan sát</td></tr>
<tr><td><b>frontend → redis-cart</b><br>TCP / 6379</td><td class="text-orange-700"><b>DROPPED</b><br>Policy denied</td><td>Truy cập trực tiếp bị policy từ chối</td></tr>
<tr><td><b>frontend → paymentservice</b><br>TCP / 50051</td><td class="text-orange-700"><b>DROPPED</b><br>Policy denied</td><td>Đường gọi bỏ qua checkoutservice bị từ chối</td></tr>
</tbody>
</table>

<div class="text-sm leading-relaxed">

- Đối chiếu **Pod nguồn / đích, cổng, thời gian, verdict và drop reason** với lần kiểm thử.
- **Timeout chưa đủ kết luận policy chặn**; `FORWARDED` cũng chưa chứng minh request ứng dụng thành công.

</div>

<div class="text-xs muted mt-4">Minh họa kết quả kỳ vọng theo policy thiết kế; cần đối chiếu flow thực tế của bài thực nghiệm.</div>

<!--
Người trình bày: phụ trách Cilium/E2. Đây là minh họa, không phải log thực tế đã thu được.
Trước demo, xác nhận endpointSelector và serviceaccount khớp Pod, enforcement bật, policy đã được thực thi; hiện kết quả frontend chỉ có DNS chưa đủ xác nhận các quyền ứng dụng đã áp dụng.
Với Hubble CLI đã kết nối Relay: hubble observe --namespace microservices-google-demo --verdict DROPPED --follow
Quan sát trên Relay để bao phủ các node, hoặc agent đúng node nếu quan sát cục bộ. Drop có nhiều nguyên nhân, phải kiểm tra Policy denied.
Hubble quan sát sự kiện datapath của Cilium; chính Cilium thực thi policy. Không gọi Hubble là thành phần chặn.
Chuyển phần: Hubble cho biết luồng mạng; tiếp theo Tetragon quan sát hành vi process/file bên trong workload.
Nguồn: https://docs.cilium.io/en/stable/observability/hubble/hubble-cli/
-->

---

# 2.2.4 E2 · Cilium ghi nhận kết nối bị policy chặn

<div class="text-base muted mb-5">Quan sát packet bị drop bằng <code>cilium-dbg monitor --type drop -v</code>.</div>

<DropMonitorExplain />

<!--
Ảnh người dùng cung cấp. Không suy diễn đây là frontend tới Redis/Payment, hoặc gán cho policy YAML cụ thể khi chưa đối chiếu identity, Pod, policy và thời điểm.
Không khẳng định reverse shell đã được kiểm thử chỉ từ địa chỉ và cổng trong ảnh.
-->

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

Trong E3, Tetragon theo dõi hook security_file_permission để bắt việc đọc serviceaccount/token — thứ File Inclusion làm ngay trong PHP worker. (File policy dùng kprobe; process_exec/exit có sẵn. Override cần kernel hỗ trợ, không mặc định đòi BPF-LSM.)
-->

---

# 2.3.2 E3 · Sau khai thác: đọc ServiceAccount token

<TetragonFlow />

<div class="small mt-2">
<v-clicks>

- **Command Injection:** chạy lệnh đọc file như `ca.crt`, ServiceAccount token → Tetragon ban đầu ghi nhận **process thực thi lệnh**
- **File Upload → File Inclusion:** PHP đọc file ngay trong worker có sẵn, không sinh process mới → **bỏ lọt khi chỉ giám sát process**
- **Thêm rule monitor file** tại `security_file_permission` → ghi nhận thao tác đọc cùng đường dẫn file và PHP worker. <span class="hl">**Monitor-only, chưa chặn**</span>

</v-clicks>
</div>

---

# 2.3.3 E3 · Ghi nhận process từ Command Injection

<div class="text-base muted mb-6">DVWA thực thi lệnh; Tetragon ghi nhận các process phát sinh trong Pod.</div>

<img src="/e3-command-injection-process.png" class="w-full rounded" alt="Log Tetragon trong Pod DVWA: process và exit của shell, ping và id" />

<div class="text-base mt-6 leading-relaxed">

- **Process:** `/bin/sh` khởi chạy `ping` và `id`; log hiển thị binary và arguments.
- **Exit:** ghi nhận kết thúc process; các dòng trong ảnh có exit status `0`.

</div>

<div class="text-sm muted mt-4">Bằng chứng cho giám sát process; ảnh này chưa thể hiện thao tác đọc file hay phát hiện File Inclusion.</div>

<!--
Ảnh do người dùng cung cấp. Lệnh tetra getevents lọc theo Pod DVWA; ví dụ shell chạy ping và id.
Không diễn giải log này thành bằng chứng đọc ca.crt/token, chặn lệnh hay file-access event.
Liên hệ bước 1 ở slide trước: Command Injection tạo process mới nên được ghi nhận; LFI đọc trực tiếp trong PHP worker cần bổ sung rule file.
-->

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
