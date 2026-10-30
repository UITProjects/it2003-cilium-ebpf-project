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
      <li>mô hình mạng Kubernetes</li>
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

# 1.1 Mô hình mạng Kubernetes & direct routing

<K8sModel />

<!--
Ba yêu cầu của mô hình mạng Kubernetes:
① Pod ↔ Pod mọi node, không NAT
② Node ↔ mọi Pod trên node
③ IP Pod tự thấy = IP người khác thấy
Inter-node (②): mỗi node có route tới podCIDR của node kia qua IP node đó → packet giữ nguyên IP Pod trên L2 network.
Service: ClusterIP ảo không gắn interface, chỉ là rule DNAT trên mỗi node (kube-proxy / eBPF) → E1.

Backup – route giữa các node được cài thế nào:
- Calico: BIRD quảng bá podCIDR của node qua BGP.
- Cilium: autoDirectNodeRoutes cài route trực tiếp (các node cùng L2).
- Direct routing: không encapsulation (không VXLAN/Geneve header) → MTU 1500 đầy đủ cho Pod.
- Cả hai cụm cùng direct routing → khác biệt trong thực nghiệm chỉ đến từ xử lý Service / policy.
- netns/veth: mỗi Pod = 1 network namespace riêng; CNI tạo cặp veth, đầu eth0 trong Pod, đầu lxc* / cali* ở host → mọi packet của Pod đi qua network stack của host.
-->

---

# 1.2 Calico · iptables: rule, chain & conntrack

<IptablesChain />

<!--
Người trình bày: Đạt. Phạm vi là Calico dùng Linux datapath iptables trong thực nghiệm này; Calico còn có chế độ eBPF.
Giải thích rule, table và chain trước, sau đó conntrack. Chỉ packet đầu tiên của kết nối đi qua xử lý NAT; trạng thái NAT được áp dụng cho các packet sau.
E1 đo kết nối mới, vì vậy cần phân biệt chi phí thiết lập kết nối với xử lý packet của kết nối đã có.
Chuyển tiếp: xem các thành phần này xuất hiện ở đâu trên đường Pod tới Pod cùng node.
-->

---

# 1.3 Cilium · Chương trình eBPF & BPF map

<EbpfIntro />

<!--
Người trình bày: Đạt. Chương trình được biên dịch thành BPF bytecode trước khi nạp qua bpf(); verifier kiểm tra và JIT biên dịch thành mã máy khi được hỗ trợ/bật.
Chương trình gắn vào hook và sử dụng BPF maps trong kernel. cilium-agent cập nhật thông tin endpoint, identity và policy; chương trình datapath cũng có thể cập nhật trạng thái như conntrack.
Các dòng trong bảng mô tả chức năng, không khẳng định mọi map đều có cùng cấu trúc hay độ phức tạp O(1).
Chuyển tiếp: so sánh đường đi packet Pod tới Pod cùng node trên hai datapath.
-->

---

# 1.4 Đường đi packet giữa hai Pod cùng node: Calico vs Cilium

<PathCompare mode="both" />

<div class="text-center mt-5">

<span class="hl">Calico: packet đi qua **Netfilter** của host · Cilium: **eBPF** tại TC tra map rồi redirect thẳng tới Pod</span>

</div>

<!--
Người trình bày: Đạt. Ví dụ dùng IP Pod trực tiếp, không minh họa bước dịch ClusterIP của Service (phần đó ở E1). IP và identity chỉ là minh họa.
Calico: packet rời Pod A qua veth (cali*) vào network stack của host; host định tuyến tới Pod B, traffic đi qua các hook Netfilter (PREROUTING, FORWARD, POSTROUTING), nơi rule iptables kiểm tra. Không phải mọi hook đều NAT mọi packet; conntrack lưu trạng thái.
Cilium: chương trình eBPF ở phía host của veth (lxc*) dùng conntrack, ipcache (IP → identity), policy map và endpoint map (4 lookup giới thiệu ở 1.3); với BPF host routing được bật và hỗ trợ, bpf_redirect_peer() chuyển packet tới Pod cục bộ mà không đi theo đường Netfilter.
Không coi các ô là thứ tự hook cố định; policy có thể thực thi ở phía endpoint nguồn hoặc đích tùy hướng traffic/cấu hình. Không suy ra kết quả hiệu năng từ hình; E1 trình bày phép đo.
-->
---
transition: slide-up | slide-down
---

# 2. Thực nghiệm · Infrastructure

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

# 2.1.2 E1 · Routing: network stack vs eBPF redirect

<RoutingCompare />

<div class="text-center mt-3">

<span class="hl">iptables: qua **network stack của host** ở cả hai node · eBPF: redirect thẳng vào **veth của Pod đích**</span>

</div>

<!--
Cùng ý với 1.4, giờ trên đường đi cross-node của E1.
Bổ sung cho sơ đồ ở 1.1: route giữa các node giống nhau (direct routing), khác nhau ở chỗ packet được xử lý trong node.
Calico: Pod → cali* → host stack (PREROUTING: kube-proxy DNAT qua KUBE-SERVICES, routing, FORWARD, POSTROUTING) → eth0; node 2 lặp lại host stack rồi vào cali* → Pod.
Cilium (BPF host routing, khi được bật và kernel hỗ trợ): eBPF tại TC của lxc* làm policy/conntrack, bpf_fib_lookup() rồi bpf_redirect_neigh() ra eth0; ở node 2, eBPF tại TC ingress của eth0 gọi bpf_redirect_peer() đưa packet thẳng vào netns của Pod.
Service trên Cilium: ClusterIP → backend được dịch ngay khi client gọi connect() (LB map), nên packet rời Pod đã mang IP backend.
Lưu ý: E1 đo khác biệt do Service lookup (O(n) vs hash). Phần bypass routing giảm chi phí per-packet nhưng E1 không tách riêng: ở N = 100, p50 iptables 2.33 ms, Cilium 2.48 ms, tức không thấy lợi thế đo được từ routing ở quy mô nhỏ.
-->

---

# 2.1.3 E1 · Kết quả

<img src="/e1-hero.png" class="mx-auto" style="max-height:440px" v-motion :initial="{ y: 40, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600 } }" />

<!--
Toàn bộ phân phối dịch chuyển (CDF, backup: public/e1-cdf.png): 10 000 vs 100 Service, median iptables +2.6 ms, Cilium khoảng −0.1 ms → mọi connection đều chịu chi phí, không riêng phần đuôi.
-->

---

# 2.1.4 E1 · Độ trễ đuôi (p99)

<img src="/e1-hero-p99.png" class="mx-auto" style="max-height:440px" v-motion :initial="{ y: 40, opacity: 0 }" :enter="{ y: 0, opacity: 1, transition: { duration: 600 } }" />

<!--
p99 = 1% request chậm nhất. Ở 10 000 Service: iptables 9.93 ms, Cilium 4.96 ms.
Phần lớn mức tăng của iptables nằm ở bước 8 020 → 10 000; p99 không tăng tuyến tính như p50, nên không vẽ đường slope.
Lợi thế của eBPF ở p99 là khả năng mở rộng, không phải mọi quy mô đều nhanh hơn.
-->

---

# 2.2.1 E2 · NetworkPolicy: IP vs identity

<PolicyTranslate />

<!--
Người trình bày: Vũ (E2, slide 12–17, gồm demo 2.2.6).
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

<img src="/e2-policy-drop-monitor.png" class="mx-auto mt-3" style="max-height:200px" />

<div class="text-xs muted mt-4">Minh họa kết quả kỳ vọng theo policy thiết kế; cần đối chiếu flow thực tế của bài thực nghiệm.</div>

<!--
Người trình bày: Vũ. Đây là minh họa, không phải log thực tế đã thu được.
Trước demo, xác nhận endpointSelector và serviceaccount khớp Pod, enforcement bật, policy đã được thực thi; hiện kết quả frontend chỉ có DNS chưa đủ xác nhận các quyền ứng dụng đã áp dụng.
Với Hubble CLI đã kết nối Relay: hubble observe --namespace microservices-google-demo --verdict DROPPED --follow
Quan sát trên Relay để bao phủ các node, hoặc agent đúng node nếu quan sát cục bộ. Drop có nhiều nguyên nhân, phải kiểm tra Policy denied.
Hubble quan sát sự kiện datapath của Cilium; chính Cilium thực thi policy. Không gọi Hubble là thành phần chặn.
Chuyển phần: Hubble cho biết luồng mạng; tiếp theo Tetragon quan sát hành vi process/file bên trong workload.
Nguồn: https://docs.cilium.io/en/stable/observability/hubble/hubble-cli/
-->

---
layout: center
class: text-center
---

# 2.2.4 E2 · Kiểm chứng NetworkPolicy trên Calico (iptables)

<div class="text-lg mb-5">Không có Hubble; xác nhận bằng <b class="text-green-800">tcpdump</b> và <b class="text-orange-700">iptables-save</b> trên node dữ liệu.</div>

<table class="w-full text-sm !mb-5">
<thead><tr><th>Luồng kiểm thử</th><th>Kết quả quan sát</th><th>Bằng chứng</th></tr></thead>
<tbody>
<tr><td><b>frontend → cartservice</b><br>TCP / 7070</td><td class="text-green-700"><b>succeeded</b></td><td>tcpdump: bắt tay 3 bước + đóng sạch (5 gói)</td></tr>
<tr><td><b>frontend → redis-cart</b><br>TCP / 6379</td><td class="text-orange-700"><b>timed out</b></td><td>iptables: <code>knp.default.boutique-redis-cart</code></td></tr>
<tr><td><b>frontend → paymentservice</b><br>TCP / 50051</td><td class="text-orange-700"><b>timed out</b></td><td>iptables: <code>knp.default.boutique-paymentservice</code></td></tr>
</tbody>
</table>

<div class="text-sm leading-relaxed">

- 15 `NetworkPolicy` chuẩn, đặt tên đối chiếu 1:1 với 15 `CiliumNetworkPolicy` (`boutique-redis-cart` ↔ `redis-cart.yaml`).
- Không có `status.conditions` như Cilium → xác nhận gián tiếp qua luật iptables (tiền tố `knp.default.<tên-policy>` do Felix tự gắn khi dịch `NetworkPolicy` chuẩn).

</div>

<img src="/e2-calico-iptables-evidence.png" class="mx-auto mt-2" style="max-height:260px" />

<div class="text-xs muted mt-2">Ảnh: kết quả `nc`/`dig` (trái) và luật iptables tương ứng (phải) — chụp từ demo-iptable-e2.mp4. Kết quả đã thu thập thực tế trên cụm Calico, không phải minh họa kỳ vọng.</div>

<!--
Người trình bày: Vũ.
Nguồn: demo-iptable-e2.mp4, frame ~00:18–01:40.
Khác Cilium: không kubectl wait --for=condition=Valid, vì NetworkPolicy chuẩn không có status.conditions.
Chuyển phần: UC5 (NodePort 32210, trang chủ tải đủ) và UC7 (chặn reverse shell DVWA, 4 lần SYN không SYN-ACK) đã có bằng chứng, trình bày trực tiếp trong video demo.
-->

---

# 2.2.5 E2 · L7 policy: lọc HTTP API của DVWA

<div class="text-sm muted -mt-2 mb-1"><code>rules.http</code> trên TCP 80: chỉ GET tới path trong allowlist được phép; API v1 không có trong danh sách.</div>

<L7Policy />

<img src="/e2-l7-denied.png" class="mx-auto mt-2" style="max-height:160px" />

<div class="text-xs muted mt-1">Ảnh: policy <code>VALID=True</code>; GET tới API v1 → <code>Access denied</code>, Hubble ghi <code>http-request DROPPED</code>. Khác hai case L3/L4 (chặn ngay SYN), ở đây <b>HTTP request</b> bị drop theo rule L7. Chỉ mới kiểm thử GET tới API v1, chưa kiểm thử các method khác.</div>

<!--
Người trình bày: Vũ.
Trước khi áp dụng policy L7, truy cập /vulnerabilities/api/v1/user/ trả về danh sách người dùng dạng JSON.
dvwa-l7-api-policy áp dụng cho Pod app=dvwa, kiểm soát ingress TCP 80 bằng rules.http: một rule riêng cho POST/PUT/PATCH/DELETE/HEAD/OPTIONS; với GET chỉ cho phép giao diện ứng dụng, tài nguyên hỗ trợ và API v2.
eBPF xử lý packet ở L3/L4 rồi chuyển traffic HTTP tới Envoy proxy trên node để kiểm tra method + path.
Kết quả: kubectl get cnp -n dvwa → dvwa-l7-api-policy và dvwa-restrict-egress VALID=True; trình duyệt báo Access denied.
hubble observe --pod dvwa/dvwa-7cb476559d-scft4 --protocol http --verdict DROPPED --follow
→ 10.8.0.10 (world) → DVWA :80 (ID 29733) http-request DROPPED (HTTP/1.1 GET .../api/v1/user/).
Giới hạn: chỉ cho thấy GET tới API v1 bị chặn, chưa cho biết các method khác khi gọi API v1.
Chuyển phần: demo trực tiếp các kết quả E2.
-->

---
layout: center
class: text-center
---

# 2.2.6 E2 · Demo

<!--
Người trình bày: Vũ. Trình tự demo trực tiếp (hoặc phát video demo-iptable-e2.mp4):
1. kubectl get networkpolicy -n microservices-google-demo (Calico, 15 object)
2. nc -zv cartservice 7070 → succeeded; nc -zv redis-cart 6379 → timed out
3. iptables-save | grep cali-pi | grep redis → tên policy boutique-redis-cart
4. Truy cập http://<node-ip>:32210 (UC5) từ trình duyệt
5. Payload reverse shell DVWA → nc -lvnp 4444 không nhận được kết nối (UC7)
Nếu còn thời gian, đối chiếu song song với Hubble/cilium-dbg monitor bên cụm Cilium.
Chuyển phần: NetworkPolicy (kể cả L7) vẫn chỉ nhìn traffic mạng; tiếp theo Tetragon quan sát hành vi process/file bên trong workload.
-->

---

# 2.3.1 E3 · Tetragon: eBPF hook ở tầng process/file

<EbpfHooks />

<!--
Người trình bày: Phương (E3, slide 18–20, gồm demo 2.3.3).
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
layout: center
class: text-center
---

# 2.3.3 E3 · Demo

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
