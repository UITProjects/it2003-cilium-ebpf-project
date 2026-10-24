<script setup lang="ts">
// veth pair as a virtual cable between the Pod netns and the root netns.
// Click 1: the host end leads into the host network stack; which datapath runs there comes later in the deck.
const cable = 'M318,124 H562'
</script>

<template>
  <svg class="vp" viewBox="0 0 920 236">
    <defs>
      <marker id="vp-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f2937" /></marker>
    </defs>

    <!-- Pod netns -->
    <rect x="16" y="20" width="330" height="200" rx="8" class="pod" />
    <text x="32" y="44" class="t-b blue">Pod · network namespace</text>
    <rect x="44" y="96" width="120" height="56" rx="5" class="ctr" />
    <text x="104" y="129" class="t-m" text-anchor="middle">app</text>
    <line x1="164" x2="198" y1="124" y2="124" class="wire" />
    <rect x="198" y="98" width="120" height="52" rx="5" class="nic" />
    <text x="258" y="120" class="t-m mono" text-anchor="middle">eth0</text>
    <text x="258" y="139" class="t-xs mono" text-anchor="middle">10.244.1.10</text>

    <!-- root netns -->
    <rect x="532" y="20" width="372" height="200" rx="8" class="root" />
    <text x="548" y="44" class="t-b">root netns (host)</text>
    <rect x="562" y="98" width="120" height="52" rx="5" class="nic hostend" />
    <text x="622" y="120" class="t-m mono" text-anchor="middle">vethXXXX</text>
    <text x="622" y="139" class="t-xs" text-anchor="middle">host end</text>

    <!-- the cable -->
    <path :d="cable" class="veth" />
    <text x="440" y="108" class="t-m b-t" text-anchor="middle">veth pair</text>
    <text x="440" y="150" class="t-xs muted" text-anchor="middle">in one end → out the other</text>
    <circle r="7" class="dot"><animateMotion :path="cable" dur="2.4s" repeatCount="indefinite" /></circle>

    <!-- 1: the host end leads into the host network stack (datapath left abstract here) -->
    <g v-click>
      <path d="M682,124 H726" class="edge" marker-end="url(#vp-a)" />
      <rect x="728" y="84" width="164" height="80" rx="6" class="stack" />
      <text x="810" y="114" class="t-m" text-anchor="middle">host network stack</text>
      <text x="810" y="134" class="t-xs" text-anchor="middle">routing · filtering · NAT</text>
      <text x="810" y="151" class="t-xs muted" text-anchor="middle">datapath set up by the CNI</text>
    </g>
  </svg>
</template>

<style scoped>
.vp { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 300px; }
.pod { fill: #eef2ff; stroke: #4f46e5; stroke-dasharray: 6 4; }
.root { fill: #f1f5f9; stroke: #6b7280; }
.ctr { fill: #fff; stroke: #374151; }
.nic { fill: #fff; stroke: #374151; }
.nic.hostend { fill: #e8eefc; }
.stack { fill: #fff; stroke: #374151; stroke-width: 1.4; }
.wire { stroke: #374151; stroke-width: 1.4; }
.edge { fill: none; stroke: #1f2937; stroke-width: 1.8; }
.veth { stroke: #2563eb; stroke-width: 6; stroke-linecap: round; }
.dot { fill: #f8fafc; stroke: #1d4ed8; stroke-width: 2.5; }
text { fill: #1f2937; }
.t-b { font-size: 15px; font-weight: 700; }
.t-m { font-size: 13px; font-weight: 600; }
.t-xs { font-size: 11px; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; font-style: italic; }
.blue { fill: #4338ca; }
.b-t { fill: #1d4ed8; }
</style>
