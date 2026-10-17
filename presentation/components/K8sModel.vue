<script setup lang="ts">
// Kubernetes network model: two nodes, each with its own Pod CIDR.
// Clicks: 1 intra-node flow, 2 node-to-node flow (no NAT), 3 Service ClusterIP = DNAT rule on every node.
const nodes = [
  { x: 20, name: 'Node 1 · 192.168.40.161', cidr: 'podCIDR 10.244.1.0/24', eth: '.161', pods: [['Pod A', '10.244.1.10'], ['Pod B', '10.244.1.11']] },
  { x: 480, name: 'Node 2 · 192.168.40.162', cidr: 'podCIDR 10.244.2.0/24', eth: '.162', pods: [['Pod C', '10.244.2.20'], ['Pod D', '10.244.2.21']] },
]
const intra = 'M105,122 V186 H340 V122'
const inter = 'M135,122 V198 H270 V350 H730 V198 H580 V122'
</script>

<template>
  <svg class="k8s" viewBox="0 0 920 384">
    <defs>
      <marker id="k8s-g" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#16a34a" /></marker>
      <marker id="k8s-b" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#2563eb" /></marker>
    </defs>

    <!-- node network -->
    <line x1="60" x2="860" y1="350" y2="350" class="wire thick" />
    <text x="460" y="374" class="t-sm" text-anchor="middle">node network 192.168.40.0/24 · direct routing</text>

    <g v-for="n in nodes" :key="n.name">
      <rect :x="n.x" y="16" width="420" height="292" rx="8" class="node" />
      <text :x="n.x + 12" y="40" class="t-b">{{ n.name }}</text>
      <text :x="n.x + 408" y="40" class="t-sm mono" text-anchor="end">{{ n.cidr }}</text>
      <!-- pods + veth -->
      <g v-for="(p, i) in n.pods" :key="p[0]">
        <line :x1="n.x + 100 + i * 220" :x2="n.x + 100 + i * 220" y1="122" y2="170" class="wire" />
        <text :x="n.x + 80 + i * 220" y="152" class="t-xs" text-anchor="end">veth</text>
        <rect :x="n.x + 25 + i * 220" y="62" width="150" height="60" rx="6" class="pod" />
        <text :x="n.x + 100 + i * 220" y="86" class="t-b" text-anchor="middle">{{ p[0] }}</text>
        <text :x="n.x + 100 + i * 220" y="106" class="t-sm mono" text-anchor="middle">eth0 {{ p[1] }}</text>
      </g>
      <!-- root netns -->
      <rect :x="n.x + 20" y="170" width="380" height="62" rx="6" class="host" />
      <text :x="n.x + 32" y="222" class="t-xs">root netns · routing · iptables / eBPF</text>
      <!-- eth0 -->
      <line :x1="n.x + 250" :x2="n.x + 250" y1="232" y2="258" class="wire" />
      <line :x1="n.x + 250" :x2="n.x + 250" y1="292" y2="350" class="wire" />
      <rect :x="n.x + 200" y="258" width="100" height="34" rx="5" class="nic" />
      <text :x="n.x + 250" y="280" class="t-sm mono" text-anchor="middle">eth0 {{ n.eth }}</text>
    </g>

    <!-- 1: intra-node -->
    <g v-click>
      <path :d="intra" class="flow green" marker-end="url(#k8s-g)" />
      <text x="230" y="160" class="t-sm green-t" text-anchor="middle">① intra-node</text>
      <circle r="6" class="dot green-d"><animateMotion :path="intra" dur="2.6s" repeatCount="indefinite" /></circle>
    </g>

    <!-- 2: node-to-node -->
    <g v-click>
      <path :d="inter" class="flow blue" marker-end="url(#k8s-b)" />
      <rect x="295" y="322" width="410" height="22" rx="4" class="hdr" />
      <text x="500" y="338" class="t-sm mono blue-t" text-anchor="middle">② src 10.244.1.10 → dst 10.244.2.20 · no NAT</text>
      <circle r="6" class="dot blue-d"><animateMotion :path="inter" dur="4.5s" repeatCount="indefinite" /></circle>
    </g>

    <!-- 3: Service -->
    <g v-click>
      <g v-for="n in nodes" :key="`svc${n.name}`">
        <rect :x="n.x + 262" y="204" width="134" height="26" rx="4" class="svc" />
        <text :x="n.x + 329" y="215" class="t-xs mono" text-anchor="middle">ClusterIP 10.96.0.10</text>
        <text :x="n.x + 329" y="227" class="t-xs" text-anchor="middle">DNAT → Pod IP</text>
      </g>
    </g>
  </svg>
</template>

<style scoped>
.k8s { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 360px; }
.node { fill: #f8fafc; stroke: #374151; stroke-width: 1.5; }
.pod { fill: #e8eefc; stroke: #374151; }
.host { fill: #f1f5f9; stroke: #6b7280; }
.nic { fill: #fff; stroke: #374151; }
.svc { fill: #f5f3ff; stroke: #7c3aed; stroke-dasharray: 4 3; }
.hdr { fill: #eff6ff; stroke: #93c5fd; }
.wire { stroke: #374151; stroke-width: 1.4; }
.wire.thick { stroke-width: 3; }
.flow { fill: none; stroke-width: 2.6; stroke-dasharray: 7 5; animation: dash 0.9s linear infinite; }
.flow.green { stroke: #16a34a; }
.flow.blue { stroke: #2563eb; }
@keyframes dash { to { stroke-dashoffset: -12; } }
.dot { stroke: #fff; stroke-width: 2; }
.green-d { fill: #16a34a; }
.blue-d { fill: #2563eb; }
text { fill: #1f2937; }
.t-b { font-size: 14px; font-weight: 700; }
.t-sm { font-size: 12px; }
.t-xs { font-size: 10.5px; }
.svc + text, .svc + text + text { font-size: 9.5px; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.green-t { fill: #15803d; font-weight: 700; }
.blue-t { fill: #1d4ed8; font-weight: 700; }
</style>
