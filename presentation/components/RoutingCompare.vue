<script setup lang="ts">
// Slide 2.1.2 (E1): the E1 request path across nodes (fortio client on node 1 → server on node 2).
// Both lanes draw the same boxes: Pod eth0 ─veth pair─ host-side veth → host network stack → eth0.
// Calico walks straight through the host stack on both nodes. Cilium (BPF host routing) jumps over it:
// bpf_redirect_neigh() from the lxc* TC program to eth0, then bpf_redirect_peer() from eth0 into the Pod.
// The host stack stays one abstract box; its hooks are in the speaker notes.
// Netns frames: the Pod's eth0 is the veth end inside the Pod netns; cali*/lxc*, the stack and the
// physical eth0 live in the root netns. bpf_redirect_peer() visibly crosses from one into the other.
const W = 920
// Node 1 boxes as [x, width]; node 2 mirrors them (x' = W - x - w).
const L = { pod: [22, 88], veth: [156, 62], stack: [240, 116], nic: [372, 54] } as const
const NS = { pod: [14, 104], root: [146, 288] } as const
const m = ([x, w]: readonly [number, number]) => [W - x - w, w] as const
const R = { pod: m(L.pod), veth: m(L.veth), stack: m(L.stack), nic: m(L.nic) }
const frames = [
  { r: NS.pod, c: 'ns-pod', t: 'Pod netns' }, { r: NS.root, c: 'ns-root', t: 'root netns' },
  { r: m(NS.pod), c: 'ns-pod', t: 'Pod netns' }, { r: m(NS.root), c: 'ns-root', t: 'root netns' },
]
const H = 56
const lanes = [
  { key: 'calico', cy: 125, title: 'Calico · iptables', veth: 'cali*' },
  { key: 'cilium', cy: 320, title: 'Cilium · eBPF', veth: 'lxc*' },
]
const cy2 = lanes[1].cy
const top2 = cy2 - H / 2
const cx = ([x, w]: readonly [number, number]) => x + w / 2
// Cilium bypass arcs, from the top of one box to the top of another.
const arc1 = `M${cx(L.veth)},${top2} C${cx(L.veth) + 40},${top2 - 80} ${cx(L.nic) - 40},${top2 - 80} ${cx(L.nic)},${top2 - 2}`
const arc2 = `M${cx(R.nic)},${top2} C${cx(R.nic) + 60},${top2 - 80} ${cx(R.pod) - 60},${top2 - 80} ${cx(R.pod)},${top2 - 2}`
// Calico's straight hops between neighbouring boxes, as [from, to] x-coordinates.
const hops = [
  [L.veth[0] + L.veth[1], L.stack[0]], [L.stack[0] + L.stack[1], L.nic[0]],
  [R.nic[0] + R.nic[1], R.stack[0]], [R.stack[0] + R.stack[1], R.veth[0]],
]
const pipes = [[L.pod[0] + L.pod[1], L.veth[0]], [R.veth[0] + R.veth[1], R.pod[0]]]
</script>

<template>
  <div class="rc">
    <svg viewBox="0 0 920 392">
      <defs>
        <marker id="rc-k" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f2937" /></marker>
        <marker id="rc-g" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#15803d" /></marker>
      </defs>

      <rect x="10" y="10" width="430" height="372" rx="8" class="node" />
      <rect x="480" y="10" width="430" height="372" rx="8" class="node" />
      <text x="24" y="36" class="t-b">Node 1 · fortio client</text>
      <text x="494" y="36" class="t-b">Node 2 · fortio server</text>

      <g v-for="ln in lanes" :key="ln.key">
        <text x="24" :y="ln.cy - 50" class="t-lane mono">{{ ln.title }}</text>

        <!-- network namespaces -->
        <g v-for="(f, i) in frames" :key="`f${i}`">
          <rect :x="f.r[0]" :y="ln.cy - 36" :width="f.r[1]" height="82" rx="7" :class="f.c" />
          <text :x="f.r[0] + 6" :y="ln.cy + 41" class="t-xs mono" :class="`${f.c}-t`">{{ f.t }}</text>
        </g>

        <!-- Pods + veth pairs -->
        <g v-for="(p, i) in [L.pod, R.pod]" :key="`p${i}`">
          <rect :x="p[0]" :y="ln.cy - H / 2" :width="p[1]" :height="H" rx="6" class="pod" />
          <text :x="cx(p)" :y="ln.cy - 4" class="t-b" text-anchor="middle">{{ i === 0 ? 'client' : 'server' }} Pod</text>
          <text :x="cx(p)" :y="ln.cy + 15" class="t-sm mono" text-anchor="middle">eth0</text>
        </g>
        <g v-for="(seg, i) in pipes" :key="`v${i}`">
          <rect :x="seg[0]" :y="ln.cy - 5" :width="seg[1] - seg[0]" height="10" class="pipe" :class="{ faint: ln.key === 'cilium' && i === 1 }" />
          <text :x="(seg[0] + seg[1]) / 2" :y="ln.cy - 10" class="t-xs muted" text-anchor="middle">veth</text>
        </g>

        <!-- host-side veth -->
        <g v-for="(v, i) in [L.veth, R.veth]" :key="`h${i}`">
          <rect :x="v[0]" :y="ln.cy - H / 2" :width="v[1]" :height="H" rx="6"
                :class="ln.key === 'calico' ? 'box' : i === 0 ? 'bpf' : 'skip'" />
          <text :x="cx(v)" :y="ln.cy + (ln.key === 'cilium' && i === 0 ? -4 : 5)" class="t-sm mono" :class="{ muted: ln.key === 'cilium' && i === 1 }" text-anchor="middle">{{ ln.veth }}</text>
          <text v-if="ln.key === 'cilium' && i === 0" :x="cx(v)" :y="ln.cy + 14" class="t-xs g-t" text-anchor="middle">eBPF TC</text>
        </g>

        <!-- host network stack: kept abstract -->
        <g v-for="(s, i) in [L.stack, R.stack]" :key="`s${i}`">
          <rect :x="s[0]" :y="ln.cy - H / 2" :width="s[1]" :height="H" rx="6" :class="ln.key === 'calico' ? 'nf' : 'skip'" />
          <text :x="cx(s)" :y="ln.cy - 4" class="t-b" :class="{ muted: ln.key === 'cilium' }" text-anchor="middle">host network</text>
          <text :x="cx(s)" :y="ln.cy + 14" class="t-b" :class="{ muted: ln.key === 'cilium' }" text-anchor="middle">stack</text>
        </g>

        <!-- NICs + wire -->
        <g v-for="(n, i) in [L.nic, R.nic]" :key="`n${i}`">
          <rect :x="n[0]" :y="ln.cy - H / 2" :width="n[1]" :height="H" rx="6" :class="ln.key === 'cilium' && i === 1 ? 'bpf' : 'box'" />
          <text :x="cx(n)" :y="ln.cy + (ln.key === 'cilium' && i === 1 ? -4 : 5)" class="t-sm mono" text-anchor="middle">eth0</text>
          <text v-if="ln.key === 'cilium' && i === 1" :x="cx(n)" :y="ln.cy + 14" class="t-xs g-t" text-anchor="middle">eBPF TC</text>
        </g>
        <line :x1="L.nic[0] + L.nic[1]" :x2="R.nic[0] - 2" :y1="ln.cy" :y2="ln.cy" class="wire" marker-end="url(#rc-k)" />
        <text x="460" :y="ln.cy - 10" class="t-xs muted" text-anchor="middle">L2</text>

        <template v-if="ln.key === 'calico'">
          <line v-for="(h, i) in hops" :key="`a${i}`" :x1="h[0]" :x2="h[1] - 2" :y1="ln.cy" :y2="ln.cy" class="hop" marker-end="url(#rc-k)" />
        </template>
      </g>

      <!-- Cilium: the bypass -->
      <path :d="arc1" class="jump" marker-end="url(#rc-g)" />
      <path :d="arc2" class="jump" marker-end="url(#rc-g)" />
      <text :x="(cx(L.veth) + cx(L.nic)) / 2" :y="top2 - 66" class="t-sm mono g-t b" text-anchor="middle">bpf_redirect_neigh()</text>
      <text :x="(cx(R.nic) + cx(R.pod)) / 2" :y="top2 - 66" class="t-sm mono g-t b" text-anchor="middle">bpf_redirect_peer()</text>
    </svg>

    <div class="legend">
      <span class="i"><i class="bx nf" /> host network stack (Netfilter + routing)</span>
      <span class="i"><i class="bx bpf" /> eBPF program at TC</span>
      <span class="i"><i class="bx skip" /> bypassed</span>
    </div>
  </div>
</template>

<style scoped>
.rc svg { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 392px; }
.node { fill: #f8fafc; stroke: #374151; stroke-width: 1.5; }
.ns-pod { fill: #f5f8ff; stroke: #93c5fd; stroke-width: 1.3; stroke-dasharray: 4 3; }
.ns-root { fill: #fff; stroke: #9ca3af; stroke-width: 1.3; stroke-dasharray: 4 3; }
.ns-pod-t { fill: #2563eb; }
.ns-root-t { fill: #6b7280; }
.pod { fill: #e8eefc; stroke: #374151; }
.box { fill: #fff; stroke: #374151; }
.nf { fill: #ffe9cc; stroke: #374151; }
.bpf { fill: #dcf5dc; stroke: #374151; }
.skip { fill: #f8fafc; stroke: #9ca3af; stroke-dasharray: 5 4; }
.pipe { fill: #e5e7eb; stroke: #374151; }
.pipe.faint { fill: #f8fafc; stroke: #9ca3af; }
.wire { stroke: #374151; stroke-width: 3; }
.hop { stroke: #1f2937; stroke-width: 2; }
.jump { fill: none; stroke: #15803d; stroke-width: 3; stroke-dasharray: 8 5; animation: dash 0.9s linear infinite; }
@keyframes dash { to { stroke-dashoffset: -13; } }
text { fill: #1f2937; }
.t-b { font-size: 13px; font-weight: 700; }
.t-lane { font-size: 14px; font-weight: 700; }
.t-sm { font-size: 12px; }
.t-xs { font-size: 10.5px; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #9ca3af; }
.g-t { fill: #15803d; }
.b { font-weight: 700; }

.legend { display: flex; justify-content: center; gap: 1.4rem; font-size: 0.78rem; margin-top: 8px; color: #1f2937; }
.legend .i { display: inline-flex; align-items: center; gap: 0.4rem; }
.legend .bx { width: 13px; height: 13px; border-radius: 3px; border: 1px solid #374151; display: inline-block; }
.legend .bx.nf { background: #ffe9cc; }
.legend .bx.bpf { background: #dcf5dc; }
.legend .bx.skip { background: #f8fafc; border: 1.2px dashed #9ca3af; }
</style>
