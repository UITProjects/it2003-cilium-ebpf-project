<script setup lang="ts">
// Slide 2.3.1 (E3): where an eBPF program can attach, grouped by the kind of event it hooks.
// File / Process hooks (what Tetragon uses) are highlighted and get most of the space;
// Network observability: Tetragon kprobe on tcp_connect, as specified for the E3 case.
const groups = [
  {
    kind: 'Network', hi: true,
    rows: [
      { hook: 'kprobe → process_kprobe', at: 'tcp_connect(struct sock *)', use: 'Ghi nhận tiến trình / Pod tạo kết nối TCP, IP và port nguồn / đích' },
    ],
  },
  {
    kind: 'File', hi: true,
    rows: [
      { hook: 'kprobe → process_kprobe', at: 'security_file_permission(file, mask)', use: 'Quan sát yêu cầu đọc file (MAY_READ); bổ sung phát hiện LFI trong PHP worker' },

    ],
  },
  {
    kind: 'Process', hi: true,
    rows: [
      { hook: 'process_exec (event)', at: 'Cơ chế giám sát thực thi có sẵn của Tetragon', use: 'Ghi nhận binary, arguments, parent khi Command Injection thực thi chương trình' },

    ],
  },
]
</script>

<template>
  <div class="eh">
    <table>
      <thead>
        <tr><th>Nhóm</th><th>Hook / Event</th><th>Hàm kernel / Nguồn sự kiện</th><th>Vai trò trong thực nghiệm</th></tr>
      </thead>
      <tbody v-for="g in groups" :key="g.kind" :class="g.hi ? 'hi' : 'lo'">
        <tr v-for="(r, i) in g.rows" :key="r.hook">
          <td v-if="i === 0" :rowspan="g.rows.length" class="kind">{{ g.kind }}</td>
          <td class="hook mono">{{ r.hook }}</td>
          <td>{{ r.at }}</td>
          <td>{{ r.use }}</td>
        </tr>
      </tbody>
    </table>

    <div class="eh-legend">
      <span class="i"><i class="bx hi"></i> network / file / process monitoring · Tetragon</span>
      
    </div>
  </div>
</template>

<style scoped>
.eh { color: #1f2937; }
table { width: 100%; border-collapse: separate; border-spacing: 0; border: 1.4px solid #374151; border-radius: 10px; overflow: hidden; }
th { background: #374151; color: #fff; text-align: left; font-size: 13px; padding: 6px 12px; }
td { padding: 4px 12px; border-top: 1px solid #cbd5e1; vertical-align: middle; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.kind { font-weight: 700; border-right: 1px solid #cbd5e1; }

/* File / Process: the focus. Green, larger, bold hook names, thick left bar. */
.hi td { background: #dcf5dc; font-size: 13px; padding-top: 9px; padding-bottom: 9px; }
.hi .kind { font-size: 17px; color: #14532d; box-shadow: inset 6px 0 0 #15803d; }
.hi .hook { font-weight: 700; color: #14532d; }
.lo + .hi tr:first-child td { border-top: 2px solid #374151; }

/* E3 network flow: application context, not a traced Tetragon hook. */
.lo td { background: #f8fafc; color: #6b7280; font-size: 11.5px; }
.lo .kind { font-size: 12.5px; }

.eh-legend { display: flex; justify-content: center; flex-wrap: wrap; gap: 1.3rem; font-size: 0.8rem; margin-top: 0.6rem; }
.eh-legend .i { display: inline-flex; align-items: center; gap: 0.4rem; }
.eh-legend .bx { width: 13px; height: 13px; border-radius: 3px; border: 1px solid #374151; display: inline-block; }
.eh-legend .bx.hi { background: #dcf5dc; border: 2px solid #15803d; }
.eh-legend .bx.lo { background: #f8fafc; border-color: #9ca3af; }

.take { margin-top: 10px; text-align: center; font-size: 15px; font-weight: 700; }
.take .g { color: #15803d; }
</style>
