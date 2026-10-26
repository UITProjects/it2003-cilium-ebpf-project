<template>
  <div class="intro">
    <EbpfVM />
    <div class="map-title">BPF map lưu trạng thái dùng chung giữa agent và chương trình eBPF</div>
    <table>
      <thead><tr><th>Thông tin</th><th>Vai trò trong Cilium</th></tr></thead>
      <tbody>
        <tr><td>Conntrack</td><td>Theo dõi trạng thái kết nối</td></tr>
        <tr><td>IP → security identity</td><td>Ánh xạ địa chỉ IP với danh tính bảo mật</td></tr>
        <tr><td>Policy</td><td>Lưu điều kiện cho phép theo identity, giao thức và cổng</td></tr>
        <tr><td>Endpoint</td><td>Thông tin endpoint để chuyển tiếp tới Pod cục bộ</td></tr>
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
td:first-child { font-weight:600; width:30%; }
</style>