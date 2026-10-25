<script setup lang="ts">
// Slide 2.3: cilium-agent pre-writes lookup rows (slow, rare); the per-packet eBPF program only reads them.
// Cards ①–④ are the same steps the packet takes on 2.4 (PathCompare), with the same example Pods.
const maps = [
  { q: 'Kết nối này đã biết chưa?', name: 'cilium_ct4_global', k: '10.0.1.5:43210 → 10.0.1.9:8080 TCP', v: 'ESTABLISHED' },
  { q: 'IP này là ai?', name: 'cilium_ipcache', k: '10.0.1.9', v: 'identity 6789' },
  { q: 'Có được phép không?', name: 'cilium_policy_* (mỗi Pod)', k: 'from 12345, TCP/8080', v: 'ALLOW' },
  { q: 'Pod đích có ở node này không?', name: 'cilium_lxc (endpoint map)', k: '10.0.1.9', v: 'lxcYYY (local)' },
]
const traits = ['key → value trong kernel', 'cập nhật từng dòng, không nạp lại chương trình', 'tra hash · O(1)']
const hooks = [
  { dev: 'lxc*', t: 'traffic của Pod', on: true },
  { dev: 'eth0 (NIC)', t: 'traffic từ ngoài node', on: false },
  { dev: 'cilium_host', t: 'traffic của host', on: false },
]
</script>

<template>
  <div class="bm">
    <div class="flow">
      <!-- 1 · input from Kubernetes -->
      <div class="col in">
        <div class="hd">Kubernetes</div>
        <div class="box k8s">
          <div class="bt">Pod + labels</div>
          <div><code>frontend</code> 10.0.1.5</div>
          <div><code>backend</code> 10.0.1.9</div>
        </div>
        <div class="box k8s">
          <div class="bt">NetworkPolicy</div>
          <div>frontend → backend</div>
          <div>TCP/8080 ✅</div>
        </div>
      </div>

      <div class="link"><div class="arrow" /></div>

      <!-- 2 · control plane -->
      <div class="col">
        <div class="hd">Control plane</div>
        <div class="box agent">
          <div class="bt mono">cilium-agent</div>
          <div class="sub">(mỗi node)</div>
          <ol>
            <li>labels → identity<div class="ex">frontend = 12345<br>backend = 6789</div></li>
            <li>tính policy cho từng Pod</li>
            <li>ghi vào BPF maps</li>
          </ol>
        </div>
      </div>

      <div class="link" v-click="1"><span class="lbl">ghi / write</span><div class="arrow" /></div>

      <!-- 3 · BPF maps in the kernel, read by eBPF programs -->
      <div class="col maps">
        <div v-click="1">
          <div class="hd">BPF maps · kernel</div>
          <div class="traits"><span v-for="t in traits" :key="t">{{ t }}</span></div>
          <div v-for="(m, i) in maps" :key="m.name" class="card">
            <span class="step-n">{{ i + 1 }}</span>
            <div class="body">
              <div class="l1"><b>{{ m.q }}</b><span class="mono name">{{ m.name }}</span></div>
              <div class="kv mono"><span>{{ m.k }}</span><span>{{ m.v }}</span></div>
            </div>
          </div>
        </div>
        <div class="tail">
          <div class="card off" v-click="1">
            <span class="mono name">cilium_lb4_services_v2 / backends_v3</span>
            <span>Service IP → Pod backend (thay kube-proxy)</span>
            <span class="tag">không dùng ở 2.4</span>
          </div>
          <div class="read" v-click="2">
            <svg viewBox="0 0 14 40" width="14" height="40">
              <defs>
                <marker id="bm-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f2937" /></marker>
              </defs>
              <path d="M7,40 V5" class="dot" marker-end="url(#bm-a)" />
            </svg>
            <span class="lbl">đọc / read</span>
          </div>
        </div>
        <div class="strip" v-click="2">
          <span class="st">eBPF programs gắn tại:</span>
          <span v-for="h in hooks" :key="h.dev" class="chip" :class="{ on: h.on }"><code>{{ h.dev }}</code> {{ h.t }}</span>
        </div>
      </div>
    </div>

    <div class="take" v-click="3">
      <span class="w">Agent ghi trước</span> (chậm, ít khi) → <span class="r">eBPF chỉ đọc mỗi packet</span> (nhanh, O(1))
    </div>
    <div class="foot">Tên map tùy phiên bản; xem <code>cilium-dbg map list</code> · identity là ví dụ</div>
  </div>
</template>

<style scoped>
.bm { font-size: 12px; line-height: 1.3; color: #1f2937; }
.flow { display: grid; grid-template-columns: 140px 26px 184px 62px 1fr; align-items: center; }
.col { display: flex; flex-direction: column; gap: 8px; }
.col.maps { align-self: start; gap: 0; }
.hd { font-size: 11px; font-weight: 700; color: #6b7280; text-align: center; margin-bottom: 2px; }
.box { border: 1px solid #374151; border-radius: 7px; padding: 6px 8px; }
.bt { font-weight: 700; margin-bottom: 2px; }
.k8s { background: #e8eefc; font-size: 11.5px; }
.agent { background: #dcf5dc; }
.agent ol { margin: 4px 0 0; padding-left: 14px; list-style: decimal; }
.agent li { margin: 3px 0; line-height: 1.3; }
.sub { font-size: 11px; margin-top: -3px; }
.ex { font-family: var(--slidev-code-font-family, monospace); font-size: 10.5px; color: #15803d; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
:deep(code) { font-size: 11px; }

/* Column links: dark arrow with triangle head, optional label above. */
.link { display: flex; flex-direction: column; align-items: center; padding: 0 4px; }
.arrow { width: 100%; height: 2px; background: #1f2937; position: relative; }
.arrow::after { content: ''; position: absolute; right: -1px; top: -4px; border-left: 7px solid #1f2937; border-top: 5px solid transparent; border-bottom: 5px solid transparent; }
.lbl { font-size: 10.5px; font-weight: 700; margin-bottom: 3px; white-space: nowrap; }

.traits { display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; margin-bottom: 6px; }
.traits span { font-size: 10px; padding: 1px 7px; border-radius: 999px; background: #f1f5f9; border: 1px solid #cbd5e1; color: #374151; }

/* One lookup table per card: question, map name, one example row (key | value). */
.card { display: flex; align-items: center; gap: 8px; background: #dcf5dc; border: 1px solid #374151; border-radius: 7px; padding: 5px 8px; margin-bottom: 5px; }
.body { flex: 1; min-width: 0; }
.l1 { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; font-size: 13px; }
.name { font-size: 11px; color: #166534; white-space: nowrap; }
.kv { display: grid; grid-template-columns: 1fr auto; margin-top: 3px; font-size: 10.5px; background: #fff; border: 1px solid #9ca3af; border-radius: 4px; }
.kv span { padding: 1px 6px; }
.kv span + span { border-left: 1px solid #9ca3af; font-weight: 700; }

.tail { display: flex; align-items: stretch; gap: 8px; }
.card.off { flex: 1; background: #f3f4f6; border-color: #d1d5db; color: #9ca3af; font-size: 10.5px; padding: 3px 8px; flex-wrap: wrap; gap: 2px 8px; margin: 0; align-self: center; }
.card.off .name { color: #9ca3af; font-size: 10px; }
.tag { font-size: 9.5px; padding: 0 6px; border-radius: 999px; border: 1px dashed #9ca3af; }
.read { display: flex; align-items: center; gap: 4px; padding-right: 14px; }
.dot { fill: none; stroke: #1f2937; stroke-width: 2; stroke-dasharray: 3 3; }

.strip { display: flex; flex-wrap: wrap; align-items: center; gap: 5px; margin-top: 2px; padding: 5px 8px; border: 1px solid #374151; border-radius: 7px; background: #fff; font-size: 11px; }
.st { font-weight: 700; }
.chip { padding: 1px 7px; border-radius: 999px; background: #f3f4f6; border: 1px solid #d1d5db; color: #6b7280; }
.chip.on { background: #dcf5dc; border: 2px solid #15803d; color: #14532d; font-weight: 700; }

.take { margin-top: 14px; text-align: center; font-size: 15px; font-weight: 700; }
.take .w { color: #1e40af; }
.take .r { color: #15803d; }
.foot { margin-top: 6px; text-align: right; font-size: 9.5px; color: #9ca3af; }
.foot code { font-size: 9.5px; }
</style>
