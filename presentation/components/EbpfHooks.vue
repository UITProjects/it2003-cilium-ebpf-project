<script setup lang="ts">
// Slide 2.3: where an eBPF program can attach, grouped by the kind of event it hooks.
// Network hooks (the Cilium datapath) are highlighted and get most of the space;
// File / Process hooks are muted context that sets up Tetragon in section 3.
const groups = [
  {
    kind: 'Network', net: true,
    rows: [
      { hook: 'TC ingress / egress', at: 'every interface, incl. veth lxc*', use: 'Cilium datapath: routing, NAT, policy' },
      { hook: 'cgroup/connect4', at: 'socket connect()', use: 'Service IP → backend at connect' },
      { hook: 'sock_ops / sk_msg', at: 'socket', use: 'sockmap: same-host shortcut' },
    ],
  },
  {
    kind: 'File', net: false,
    rows: [
      { hook: 'kprobe security_file_permission', at: 'kernel function', use: 'file read / write events' },
      { hook: 'LSM file_open', at: 'LSM security check', use: 'allow / deny file open' },
    ],
  },
  {
    kind: 'Process', net: false,
    rows: [
      { hook: 'tracepoint sched_process_exec', at: 'static kernel event', use: 'new process (exec)' },
      { hook: 'tracepoint sched_process_exit', at: 'static kernel event', use: 'process exit' },
    ],
  },
]
</script>

<template>
  <div class="eh">
    <table>
      <thead>
        <tr><th>Kind</th><th>Hook</th><th>Attach point</th><th>Used for</th></tr>
      </thead>
      <tbody v-for="g in groups" :key="g.kind" :class="g.net ? 'net' : 'other'">
        <tr v-for="(r, i) in g.rows" :key="r.hook">
          <td v-if="i === 0" :rowspan="g.rows.length" class="kind">{{ g.kind }}</td>
          <td class="hook mono">{{ r.hook }}</td>
          <td>{{ r.at }}</td>
          <td>{{ r.use }}</td>
        </tr>
      </tbody>
    </table>

    <div class="eh-legend">
      <span class="i"><i class="bx net"></i> network hook · Cilium datapath</span>
      <span class="i"><i class="bx other"></i> other hooks · file / process</span>
    </div>
    <div class="take">
      <span class="g">Cilium datapath = network hooks</span> · file/process hooks → Tetragon (phần 3)
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

/* Network: the focus. Green, larger, bold hook names, thick left bar. */
.net td { background: #dcf5dc; font-size: 15px; padding-top: 9px; padding-bottom: 9px; }
.net .kind { font-size: 17px; color: #14532d; box-shadow: inset 6px 0 0 #15803d; }
.net .hook { font-weight: 700; color: #14532d; }
.net + .other tr:first-child td { border-top: 2px solid #374151; }

/* Other kinds: muted context. */
.other td { background: #f8fafc; color: #6b7280; font-size: 11.5px; }
.other .kind { font-size: 12.5px; }

.eh-legend { display: flex; justify-content: center; flex-wrap: wrap; gap: 1.3rem; font-size: 0.8rem; margin-top: 0.6rem; }
.eh-legend .i { display: inline-flex; align-items: center; gap: 0.4rem; }
.eh-legend .bx { width: 13px; height: 13px; border-radius: 3px; border: 1px solid #374151; display: inline-block; }
.eh-legend .bx.net { background: #dcf5dc; border: 2px solid #15803d; }
.eh-legend .bx.other { background: #f8fafc; border-color: #9ca3af; }

.take { margin-top: 10px; text-align: center; font-size: 15px; font-weight: 700; }
.take .g { color: #15803d; }
</style>
