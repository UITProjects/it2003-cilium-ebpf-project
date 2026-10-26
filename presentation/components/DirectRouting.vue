<script setup lang="ts">
// Inter-node traffic with direct (native) routing, as configured on both clusters.
// Each node routes the other node's Pod CIDR via that node's IP; the packet crosses the L2 network unchanged.
// Click 1: the packet path + its header.
const nodes = [
  { x: 20, name: 'Node 1 · 192.168.40.161', pod: ['Pod A', '10.244.1.10'], eth: '.161', routes: ['10.244.1.0/24 dev lxc*/cali*', '10.244.2.0/24 via 192.168.40.162'] },
  { x: 520, name: 'Node 2 · 192.168.40.162', pod: ['Pod C', '10.244.2.20'], eth: '.162', routes: ['10.244.2.0/24 dev lxc*/cali*', '10.244.1.0/24 via 192.168.40.161'] },
]
const flow = 'M100,104 V240 H285 V292 H785 V240 H600 V104'
</script>

<template>
  <svg class="dr" viewBox="0 0 920 340">
    <defs>
      <marker id="dr-b" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#2563eb" /></marker>
    </defs>

    <line x1="60" x2="860" y1="292" y2="292" class="wire thick" />
    <text x="460" y="326" class="t-sm" text-anchor="middle">L2 network 192.168.40.0/24</text>

    <g v-for="(n, k) in nodes" :key="n.name">
      <rect :x="n.x" y="10" width="380" height="240" rx="8" class="node" />
      <text :x="n.x + 14" y="34" class="t-b">{{ n.name }}</text>
      <rect :x="n.x + 20" y="54" width="120" height="50" rx="6" class="pod" />
      <text :x="n.x + 80" y="75" class="t-b" text-anchor="middle">{{ n.pod[0] }}</text>
      <text :x="n.x + 80" y="94" class="t-sm mono" text-anchor="middle">{{ n.pod[1] }}</text>

      <rect :x="n.x + 152" y="54" width="214" height="104" rx="6" class="rt" />
      <text :x="n.x + 162" y="74" class="t-sm mono muted">$ ip route</text>
      <text :x="n.x + 162" y="100" class="t-xs mono">{{ n.routes[0] }}</text>
      <rect :x="n.x + 157" y="114" width="204" height="24" rx="4" class="via" />
      <text :x="n.x + 162" y="131" class="t-xs mono via-t">{{ n.routes[1] }}</text>

      <line :x1="n.x + 265" :x2="n.x + 265" y1="250" y2="292" class="wire" />
      <rect :x="n.x + 210" y="198" width="110" height="32" rx="5" class="nic" />
      <text :x="n.x + 265" y="219" class="t-sm mono" text-anchor="middle">eth0 {{ n.eth }}</text>
    </g>

    <g v-click>
      <path :d="flow" class="flow" marker-end="url(#dr-b)" />
      <rect x="340" y="256" width="390" height="26" rx="4" class="hdr" />
      <text x="535" y="274" class="t-sm mono hdr-t" text-anchor="middle">IP src 10.244.1.10 → dst 10.244.2.20</text>
      <circle r="6" class="dot"><animateMotion :path="flow" dur="4s" repeatCount="indefinite" /></circle>
    </g>
  </svg>
</template>

<style scoped>
.dr { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 350px; }
.node { fill: #f8fafc; stroke: #374151; stroke-width: 1.5; }
.pod { fill: #e8eefc; stroke: #374151; }
.rt { fill: #fff; stroke: #9ca3af; }
.via { fill: #eff6ff; stroke: #93c5fd; }
.nic { fill: #fff; stroke: #374151; }
.hdr { fill: #eff6ff; stroke: #93c5fd; }
.wire { stroke: #374151; stroke-width: 1.4; }
.wire.thick { stroke-width: 3; }
.flow { fill: none; stroke: #2563eb; stroke-width: 2.6; stroke-dasharray: 7 5; animation: dash 0.9s linear infinite; }
@keyframes dash { to { stroke-dashoffset: -12; } }
.dot { fill: #2563eb; stroke: #fff; stroke-width: 2; }
text { fill: #1f2937; }
.t-b { font-size: 14px; font-weight: 700; }
.t-sm { font-size: 12px; }
.t-xs { font-size: 11px; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; }
.via-t, .hdr-t { fill: #1d4ed8; font-weight: 700; }
</style>
