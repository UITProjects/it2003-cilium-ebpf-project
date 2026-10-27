<template>
  <div class="explain">
    <div class="capture">
      <img src="/e2-policy-drop-monitor.png" alt="Log Cilium monitor với các vùng được đánh dấu" />
      <div class="mark one"><span>1</span></div>
      <div class="mark two"><span>2</span></div>
      <div class="mark three"><span>3</span></div>
      <div class="mark four"><span>4</span></div>
    </div>
    <div class="notes">
      <div><b class="blue">1 · Công cụ quan sát</b><p><code>--type drop -v</code>: xem sự kiện drop với thông tin chi tiết.</p></div>
      <div><b class="orange">2 · Lý do bị chặn</b><p><code>Policy denied</code>: packet bị từ chối theo policy.</p></div>
      <div><b class="green">3 · Nguồn → đích</b><p><code>10.244.1.159:45828</code><br>→ <code>10.8.0.10:1234</code><br>IP:cổng nguồn → IP:cổng đích.</p></div>
      <div><b class="purple">4 · Loại packet</b><p><code>tcp SYN</code>: packet mở đầu kết nối TCP. Các lần thử tiếp theo cũng bị drop.</p></div>
    </div>
  </div>
  <div class="foot">Identity 29733 → world: danh tính nguồn → đích. “Unsupported L3 protocol” là sự kiện khác, không gộp vào kết luận policy chặn TCP.</div>
</template>
<style scoped>
.explain { display:grid; grid-template-columns: 2.35fr 1fr; gap:20px; align-items:start; margin-top:18px; }
.capture { position:relative; }
.capture img { display:block; width:100%; border-radius:5px; }
.mark { position:absolute; border:0; border-radius:2px; pointer-events:none; box-sizing:border-box; }
.mark span { display:none; position:absolute; top:-12px; left:-12px; width:20px; height:20px; border-radius:50%; color:white; font-size:12px; line-height:20px; text-align:center; font-weight:700; }
.one { left:26%; top:6%; width:68%; height:7%; background:rgba(96,165,250,0.23); }.one span {background:#2563eb;}
.two { left:8%; top:46.5%; width:20%; height:5.5%; background:rgba(251,146,60,0.23); }.two span {background:#c2410c;}
.three { left:10%; top:52%; width:39%; height:5.5%; background:rgba(74,222,128,0.23); }.three span {background:#15803d;}
.four { left:49%; top:52%; width:9%; height:5.5%; background:rgba(192,132,252,0.23); }.four span {background:#7e22ce;}
.notes { font-size:12px; line-height:1.35; }.notes > div { margin-bottom:13px; }.notes b {font-size:14px;}.notes p {margin:4px 0 0;}.notes code {font-size:11px;}
.blue{color:#2563eb}.orange{color:#c2410c}.green{color:#15803d}.purple{color:#7e22ce}
.foot {font-size:11px;line-height:1.5;color:#64748b;margin-top:16px;}
</style>