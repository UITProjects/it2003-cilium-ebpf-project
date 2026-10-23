# Kịch bản kiểm thử Cilium Online Boutique

Hướng dẫn chạy cập nhật nằm trong [README: chuẩn bị debugger và sáu use case](README.md). README dùng tên debugger mới theo thời gian để không phụ thuộc container `debugger-8s6qc` trong các lệnh mẫu dưới đây. T1–T6 ở tài liệu này tương ứng UC1–UC6 trong README; các kết quả ngày 22/10/2026 là kết quả đã quan sát trước đây.

## Mục tiêu và điều kiện

Chứng minh luồng hợp lệ được phép và các nỗ lực lateral movement qua luồng ngoài sơ đồ bị chặn. Các bài TCP chỉ kiểm tra kết nối mạng, không chứng minh method gRPC hay nghiệp vụ đã thành công.

Từ thư mục `D:\NT2205.11.CH-Project-2\cilium`:

```powershell
kubectl get cnp -n microservices-google-demo
kubectl wait -n microservices-google-demo --for=condition=Valid cnp --all --timeout=30s
kubectl get pods -n microservices-google-demo -o wide
```

Giải thích:

- `get cnp`: liệt kê các CiliumNetworkPolicy; `-n` chọn namespace của ứng dụng.
- `wait --for=condition=Valid`: chờ Cilium xác nhận policy hợp lệ; `--all` áp dụng cho tất cả CNP trong namespace; `--timeout=30s` chờ tối đa 30 giây.
- `get pods -o wide`: xem Pod, IP và node đang chạy để chọn đúng nguồn test và agent quan sát.

Tất cả 15 CNP phải có `VALID=True`. Dry-run chỉ kiểm tra qua API server, chưa đủ để khẳng định Cilium đã nhận rule. Bản default deny cũ dùng `ingress: []` và `egress: []` đã bị agent từ chối; bản sửa dùng một phần tử `{}` cho mỗi hướng và đã được xác nhận `Valid=True`.

## Quan sát Hubble

Nếu có Hubble CLI kết nối relay, mở một terminal riêng:

```powershell
hubble observe --namespace microservices-google-demo --verdict DROPPED --follow
```

`observe` xem luồng mạng; `--namespace` lọc namespace; `--verdict DROPPED` chỉ hiển thị các flow bị loại bỏ; `--follow` tiếp tục theo dõi flow mới. Xem thêm lý do drop để phân biệt policy chặn với lỗi mạng khác.

Cluster hiện có Hubble trong Cilium agent; không cần cài CLI lên Windows để xem log cục bộ:

```powershell
# Agent cùng node frontend thật tại thời điểm kiểm tra
kubectl exec -n kube-system cilium-fmxwl -- hubble observe --namespace microservices-google-demo --verdict DROPPED --since 5m --last 30

```

`kubectl exec` chạy lệnh bên trong Pod Cilium; `-n kube-system` là namespace chứa agent. Dấu `--` ngăn cách tham số của kubectl với lệnh chạy trong container. `--since 5m` giới hạn về 5 phút gần nhất và `--last 30` lấy tối đa 30 flow cuối trong khoảng đó.

Đối chiếu node bằng `kubectl get pods -n kube-system -l k8s-app=cilium -o wide` và `kubectl get pods -n microservices-google-demo -o wide`. Agent cục bộ không cung cấp toàn bộ flow của cluster. Tên Pod/agent có thể đổi sau khi tạo lại.

Trong lệnh đối chiếu, `-l k8s-app=cilium` chỉ chọn Pod có label của Cilium agent; `-o wide` hiển thị thêm node và IP.

## Ma trận test

| ID | Kịch bản | Kỳ vọng | Kết quả đã quan sát ngày 22/10/2026 |
|---|---|---|---|
| T1 | frontend thật phân giải DNS Redis | Cho phép DNS | Cần chạy lại từ debugger của frontend |
| T2 | frontend thật → cart:7070 | Cho phép | TCP thành công |
| T3 | frontend thật → Redis:6379 | Chặn truy cập trực tiếp dữ liệu | Timeout và Hubble Policy denied |
| T4 | frontend thật → payment:50051 | Chặn bỏ qua checkout | Timeout và Hubble Policy denied |
| T5 | Client ngoài → NodePort của Service LoadBalancer → frontend | Cho phép | Cần chạy lại qua NodePort của thực nghiệm |
| T6 | Xem sản phẩm, thêm giỏ, đổi tiền, checkout | Chức năng hoạt động khi dependency Ready | Chưa hoàn tất; email/recommendation đang replicas=0 |

Timeout chỉ được xem là bằng chứng policy chặn khi có flow `Policy denied` tương ứng về nguồn, đích, port và thời điểm. Lỗi `connection refused`, DNS failure hoặc không có endpoint không đủ để kết luận policy hoạt động đúng.

## T1: DNS vẫn hoạt động

```powershell
kubectl exec -n microservices-google-demo frontend-fdd86794-kwckr -c debugger-8s6qc -- dig +short +time=2 +tries=1 redis-cart.microservices-google-demo.svc.cluster.local
```

Giải thích:

- `kubectl exec ... frontend-fdd86794-kwckr`: thực hiện truy vấn từ Pod frontend thật.
- `-c debugger-8s6qc`: chọn debugger có công cụ DNS, dùng chung mạng với frontend. Cách kiểm tra hoặc mở debugger được mô tả trong T2.
- `dig`: công cụ truy vấn DNS; tên cuối lệnh là tên DNS đầy đủ của Service Redis.
- `+short`: chỉ in kết quả ngắn gọn; `+time=2`: thời gian chờ phản hồi DNS là 2 giây; `+tries=1`: chỉ thử một lần.

Kỳ vọng: trả về ClusterIP Redis. Nếu DNS lỗi, chưa nên kết luận từ các test dùng tên Service tiếp theo.

## T2: Frontend gọi Cart đúng sơ đồ

Frontend dùng image không có shell/công cụ mạng. Pod hiện có sẵn ephemeral container đang chạy tên `debugger-8s6qc`; dùng container này để test từ đúng network namespace và danh tính mạng của frontend:

```powershell
kubectl exec -n microservices-google-demo frontend-fdd86794-kwckr -c debugger-8s6qc -- nc -zv -w 3 cartservice 7070
```

Giải thích:

- `frontend-fdd86794-kwckr`: Pod nguồn thực hiện kết nối; `-n` chọn namespace ứng dụng.
- `-c debugger-8s6qc`: chọn container có công cụ mạng nằm trong Pod frontend.
- `--`: phần phía sau là lệnh chạy trong container.
- `nc`: công cụ kiểm tra kết nối; mặc định dùng TCP trong lệnh này.
- `-z`: chỉ kiểm tra cổng, không gửi dữ liệu ứng dụng; `-v`: in thông tin kết nối; `-w 3`: đặt timeout kết nối là 3 giây.
- `cartservice 7070`: Service đích và cổng TCP cần kiểm tra.

Kỳ vọng: `succeeded`, exit code 0. Nếu Pod hoặc debugger đã đổi, tìm container đang chạy trong `kubectl describe pod <frontend-pod> -n microservices-google-demo`. Khi không còn debugger, quản trị viên có thể mở tạm bằng lệnh sau và chạy các lệnh `nc` trong shell đó:

```powershell
kubectl debug -it -n microservices-google-demo pod/<frontend-pod> --image=nicolaka/netshoot --target=server -- /bin/bash
```

`debug` thêm ephemeral container để chẩn đoán; `-it` mở terminal tương tác; `--image` chọn image có công cụ mạng. `--target=server` yêu cầu nhắm tới process namespace của container `server` nếu runtime hỗ trợ; việc dùng chung mạng là do debugger nằm trong cùng Pod. `/bin/bash` là shell mở trong debugger. Từ shell này, chạy trực tiếp `nc -zv -w 3 cartservice 7070`.

Thay `<frontend-pod>` bằng tên thực. Ephemeral container dùng network của Pod hiện tại, không phải Pod mới giả label frontend. Thoát bằng `exit`; Kubernetes vẫn giữ metadata của ephemeral container đến khi Pod được tạo lại.

## T3: Frontend không được truy cập Redis trực tiếp

```powershell
kubectl exec -n microservices-google-demo frontend-fdd86794-kwckr -c debugger-8s6qc -- nc -zv -w 3 redis-cart 6379
```

Lệnh chạy từ debugger trong Pod frontend thật. `redis-cart` là Service Redis, `6379` là cổng TCP Redis. `-z` chỉ thăm dò cổng, `-v` in kết quả, `-w 3` giới hạn thời gian chờ kết nối là 3 giây. So với T2, chỉ đổi đích từ Cart sang Redis để kiểm tra frontend có bị ngăn đi thẳng tới cache hay không.

Kỳ vọng: timeout/exit code khác 0; Hubble có `frontend → redis-cart:6379`, `Policy denied`. Mô phỏng frontend bị chiếm quyền cố truy cập cache. Ứng dụng phải truy cập giỏ hàng qua cartservice.

## T4: Frontend không được bỏ qua Checkout để gọi Payment

```powershell
kubectl exec -n microservices-google-demo frontend-fdd86794-kwckr -c debugger-8s6qc -- nc -zv -w 3 paymentservice 50051
```

Nguồn vẫn là Pod frontend, được chọn qua `kubectl exec` và `-c debugger-8s6qc`. Đích `paymentservice 50051` là cổng gRPC của Payment. `nc -zv -w 3` chỉ thử thiết lập TCP, in kết quả và chờ tối đa 3 giây cho kết nối; không gọi method gRPC hay thực hiện giao dịch.

Kỳ vọng: timeout và policy drop. Chỉ checkoutservice được gọi payment theo sơ đồ. Đây là test kết nối TCP, không gửi thanh toán.

## T5: Kiểm tra truy cập từ bên ngoài

`frontend-external` hiện có **type LoadBalancer**, VIP `192.168.40.130`, Service port `80`, NodePort `30183`, Pod port `8080`. Test dưới dùng đường NodePort của Service này; không có Service NodePort riêng trong mô tả.

Trên máy có đường mạng tới node, xem IP node và NodePort trước:

```powershell
kubectl get nodes -o wide
kubectl get svc frontend-external -n microservices-google-demo
$NodeIP = '192.168.40.161'
$NodePort = kubectl get svc frontend-external -n microservices-google-demo -o jsonpath="{.spec.ports[0].nodePort}"
$FrontendUrl = "http://${NodeIP}:$NodePort"
curl.exe --connect-timeout 3 --max-time 15 -I $FrontendUrl
```

Giải thích:

- `curl.exe`: chạy curl trên Windows để gửi request từ máy client bên ngoài cluster.
- `get nodes -o wide`: hiển thị IP node; thay `$NodeIP` bằng node mà máy bạn truy cập được.
- `get svc` và JSONPath: xem Service và lấy NodePort đầu tiên, hiện là `30183`; thay `frontend-external` nếu môi trường dùng tên Service khác.
- `TYPE=LoadBalancer` và `PORT(S)=80:30183/TCP` có nghĩa Service LoadBalancer cũng có NodePort; không phải `TYPE=NodePort`.
- `--connect-timeout 3`: chờ tối đa 3 giây cho giai đoạn thiết lập kết nối.
- `--max-time 15`: giới hạn tổng thời gian lệnh ở 15 giây.
- `-I`: gửi HTTP HEAD, chỉ lấy header phản hồi.
- `$FrontendUrl`: URL `http://<IP-node>:<NodePort>`, ví dụ `http://192.168.40.161:30183`. NodePort chuyển tới Pod frontend TCP 8080.

Kỳ vọng: nhận được HTTP response; không yêu cầu HEAD phải trả 200. Nếu timeout, xem Hubble để phân biệt policy drop với lỗi route, firewall node hoặc NodePort.

Có thể đối chiếu thêm đường VIP của cùng Service bằng `curl.exe --connect-timeout 3 --max-time 15 -I http://192.168.40.130/`. Tham số giữ nguyên, chỉ đổi địa chỉ đích; thực hiện khi máy client có đường mạng tới VIP.

## T6: Kiểm tra nghiệp vụ trên trình duyệt

Mở URL NodePort đã xác định ở T5, ví dụ `http://192.168.40.161:30183/`, và thực hiện lần lượt:

1. Xem danh sách và chi tiết sản phẩm.
2. Thêm sản phẩm vào giỏ và thay đổi số lượng.
3. Đổi loại tiền tệ.
4. Checkout bằng dữ liệu demo.

Bài này thao tác trực tiếp trên UI, không có tham số dòng lệnh. URL dùng IP node và NodePort frontend; các thao tác tạo request từ frontend tới các backend theo sơ đồ. Kỳ vọng các bước thành công khi các dependency đều Ready.

Nếu nhận HTTP 5xx, kiểm tra endpoint/dependency trước khi kết luận network policy sai. Tại thời điểm kiểm tra, email và recommendation đang có replicas=0; cần khôi phục chúng theo kế hoạch trước khi test nghiệp vụ đầy đủ.

Tham khảo: [Cilium Hubble CLI](https://docs.cilium.io/en/stable/observability/hubble/hubble-cli/).
