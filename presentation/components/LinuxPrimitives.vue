<script setup lang="ts">
// High-level view of the Linux primitives behind a Pod's network.
// Static (no clicks): the veth pair into the root netns, and the CNI ADD that wires it up.
// Only the packet path (eth0 → veth → lxc*/cali* → routes → eth0) is colored; the rest is grey context.
const ctrs = [
  { x: 70, t: 'pause', s: 'holds the netns' },
  { x: 185, t: 'app', s: 'container' },
  { x: 300, t: 'sidecar', s: 'container' },
]
</script>

<template>
  <svg class="lp" viewBox="0 0 920 352">
    <defs>
      <marker id="lp-g" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9ca3af" /></marker>
    </defs>

    <rect x="16" y="8" width="888" height="336" rx="10" class="node" />
    <text x="32" y="32" class="t-b muted">Node (Linux host)</text>

    <!-- Pod netns -->
    <rect x="40" y="50" width="380" height="210" rx="8" class="pod" />
    <text x="56" y="74" class="t-b muted">Pod · network namespace</text>
    <g v-for="c in ctrs" :key="c.t">
      <rect :x="c.x" y="92" width="100" height="52" rx="5" class="ctr" />
      <text :x="c.x + 50" y="114" class="t-m faint" text-anchor="middle">{{ c.t }}</text>
      <text :x="c.x + 50" y="132" class="t-xs faint" text-anchor="middle">{{ c.s }}</text>
    </g>
    <text x="230" y="168" class="t-xs faint" text-anchor="middle">shared IP · ports · localhost</text>
    <line x1="235" x2="235" y1="174" y2="200" class="wire" />
    <rect x="175" y="200" width="120" height="38" rx="5" class="hl" />
    <text x="235" y="216" class="t-m mono hl-t" text-anchor="middle">eth0</text>
    <text x="235" y="231" class="t-xs mono hl-t" text-anchor="middle">10.244.1.10</text>

    <!-- root netns -->
    <rect x="450" y="50" width="430" height="210" rx="8" class="root" />
    <text x="466" y="74" class="t-b muted">root netns (host)</text>
    <rect x="626" y="180" width="248" height="58" rx="5" class="hl" />
    <text x="750" y="205" class="t-b mono hl-t" text-anchor="middle">routes</text>
    <text x="750" y="225" class="t-xs muted" text-anchor="middle">iptables / eBPF: slides 1.3–1.6</text>
    <line x1="750" x2="750" y1="238" y2="290" class="path" />
    <rect x="690" y="290" width="120" height="36" rx="5" class="hl" />
    <text x="750" y="313" class="t-m mono hl-t" text-anchor="middle">eth0 (node)</text>

    <!-- 1: veth pair -->
    <g>
      <line x1="295" x2="480" y1="219" y2="219" class="veth" />
      <text x="388" y="210" class="t-m hl-t" text-anchor="middle">veth pair</text>
      <rect x="480" y="200" width="120" height="38" rx="5" class="hl" />
      <text x="540" y="224" class="t-m mono hl-t" text-anchor="middle">lxc* / cali*</text>
      <line x1="600" x2="626" y1="219" y2="219" class="path" />
    </g>

    <!-- 2: CNI ADD -->
    <g>
      <rect x="640" y="88" width="220" height="58" rx="6" class="cni" />
      <text x="750" y="112" class="t-m muted" text-anchor="middle">container runtime → CNI</text>
      <text x="750" y="132" class="t-xs mono muted" text-anchor="middle">ADD / DEL</text>
      <path d="M640,117 H426" class="call" marker-end="url(#lp-g)" />
      <text x="533" y="108" class="t-xs muted" text-anchor="middle">create veth · IPAM → IP</text>
      <path d="M750,146 V180" class="call" marker-end="url(#lp-g)" />
      <text x="758" y="168" class="t-xs muted">add route</text>
    </g>
  </svg>
</template>

<style scoped>
.lp { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 400px; }
/* context: neutral greys */
.node { fill: #fafafa; stroke: #d1d5db; stroke-width: 1.5; }
.pod { fill: #fafafa; stroke: #9ca3af; stroke-dasharray: 6 4; }
.root { fill: #f5f5f5; stroke: #d1d5db; }
.ctr { fill: #fff; stroke: #d1d5db; }
.cni { fill: #fafafa; stroke: #9ca3af; stroke-dasharray: 4 3; }
.wire { stroke: #d1d5db; stroke-width: 1.4; }
.call { fill: none; stroke: #9ca3af; stroke-width: 1.6; stroke-dasharray: 6 4; }
/* focus: the packet path */
.hl { fill: #e8eefc; stroke: #2563eb; stroke-width: 2; }
.path { stroke: #2563eb; stroke-width: 2.4; }
.veth { stroke: #2563eb; stroke-width: 4; stroke-linecap: round; }
text { fill: #1f2937; }
.t-b { font-size: 15px; font-weight: 700; }
.t-m { font-size: 13px; font-weight: 600; }
.t-xs { font-size: 11px; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; }
.faint { fill: #9ca3af; }
.hl-t { fill: #1e3a8a; font-weight: 700; }
</style>
