<template>
  <div class="intro">
    <EbpfVM />
    <div class="map-title">BPF map: bảng dữ liệu trong kernel mà cilium-agent và chương trình eBPF cùng đọc/ghi</div>
    <table>
      <thead><tr><th>BPF map</th><th>Dùng để làm gì</th></tr></thead>
      <tbody>
        <tr><td>conntrack</td><td>Ghi nhớ các connection đang mở → packet tiếp theo không phải kiểm tra lại từ đầu</td></tr>
        <tr><td>ipcache <span class="sub">IP → identity</span></td><td>Tra một IP thuộc identity nào (identity = nhóm Pod có cùng label)</td></tr>
        <tr><td>policy map</td><td>Với từng Pod: identity nào được phép kết nối tới port / protocol nào</td></tr>
        <tr><td>endpoint map</td><td>Các Pod đang chạy trên node → đích là Pod cục bộ thì redirect thẳng tới đó</td></tr>
      </tbody>
    </table>
  </div>
</template>
<style scoped>
.intro :deep(.vm) { max-height: 220px; }
.map-title { font-size:15px; font-weight:600; margin:12px 0 8px; color:#14532d; }
table { width:100%; border-collapse:collapse; font-size:13px; }
th { text-align:left; background:#ecf7ee; }
th, td { padding:5px 12px; border-bottom:1px solid #dbe4dc; }
td:first-child { font-weight:600; width:30%; font-family: var(--slidev-code-font-family, monospace); }
.sub { font-weight:400; font-size:11.5px; color:#6b7280; margin-left:6px; }
</style>