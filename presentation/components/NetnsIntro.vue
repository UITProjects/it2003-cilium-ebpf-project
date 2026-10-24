<script setup lang="ts">
// Linux namespaces at a glance, then the one Kubernetes networking is built on: net.
// Click 1: two network namespaces side by side, each with its own copy of the network stack.
const kinds = [
  { k: 'mnt', d: 'mount points / filesystem' },
  { k: 'pid', d: 'process IDs' },
  { k: 'net', d: 'network stack' },
  { k: 'ipc', d: 'shared memory, queues' },
  { k: 'uts', d: 'hostname' },
  { k: 'user', d: 'UID / GID mapping' },
  { k: 'cgroup', d: 'cgroup root view' },
  { k: 'time', d: 'system clocks' },
]
const rows = ['interfaces', 'routing table', 'ARP / neighbors', 'iptables · conntrack', 'sockets · ports']
const ns = [
  { x: 336, t: 'root netns (host)', c: 'root', v: ['lo · eth0 192.168.40.161', 'node routes', 'node neighbors', 'host rules', ':22 · :10250'] },
  { x: 650, t: 'Pod netns', c: 'pod', v: ['lo · eth0 10.244.1.10', 'default → host', 'own table', 'own (separate)', ':80'] },
]
</script>

<template>
  <svg class="ni" viewBox="0 0 920 330">
    <!-- left: the 8 namespace types -->
    <text x="150" y="24" class="t-h" text-anchor="middle">Linux namespaces</text>
    <g v-for="(n, i) in kinds" :key="n.k">
      <rect x="16" :y="38 + i * 33" width="268" height="27" rx="5" class="kind" :class="{ net: n.k === 'net' }" />
      <text x="30" :y="56 + i * 33" class="t-m mono" :class="{ 'net-t': n.k === 'net' }">{{ n.k }}</text>
      <text x="96" :y="56 + i * 33" class="t-xs" :class="{ 'net-t': n.k === 'net' }">{{ n.d }}</text>
    </g>
    <text x="150" y="322" class="t-xs muted" text-anchor="middle">a container = a process + its namespaces</text>

    <!-- right: net namespace = an isolated copy of the network stack -->
    <g v-click>
      <path d="M284,119 C306,119 306,60 330,60" class="link" />
      <text x="620" y="24" class="t-h" text-anchor="middle">net namespace = its own network stack</text>
      <g v-for="n in ns" :key="n.t">
        <rect :x="n.x" y="38" width="254" height="286" rx="8" :class="n.c" />
        <text :x="n.x + 14" y="60" class="t-b" :class="{ blue: n.c === 'pod' }">{{ n.t }}</text>
        <g v-for="(r, i) in rows" :key="r">
          <rect :x="n.x + 12" :y="74 + i * 49" width="230" height="41" rx="5" class="res" />
          <text :x="n.x + 22" :y="91 + i * 49" class="t-s">{{ r }}</text>
          <text :x="n.x + 22" :y="106 + i * 49" class="t-xs mono">{{ n.v[i] }}</text>
        </g>
      </g>
      <line x1="620" x2="620" y1="70" y2="300" class="gap" />
      <rect x="593" y="166" width="54" height="34" rx="4" class="gap-bg" />
      <text x="620" y="180" class="t-xs gap-t" text-anchor="middle">isolated</text>
      <text x="620" y="194" class="t-xs gap-t" text-anchor="middle">no link</text>
    </g>
  </svg>
</template>

<style scoped>
.ni { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 360px; }
.kind { fill: #f8fafc; stroke: #9ca3af; }
.kind.net { fill: #e8eefc; stroke: #2563eb; stroke-width: 2; }
.root { fill: #f1f5f9; stroke: #6b7280; }
.pod { fill: #eef2ff; stroke: #4f46e5; stroke-dasharray: 6 4; }
.res { fill: #fff; stroke: #374151; }
.link { fill: none; stroke: #2563eb; stroke-width: 2; stroke-dasharray: 5 4; }
.gap { stroke: #dc2626; stroke-width: 1.6; stroke-dasharray: 6 5; }
text { fill: #1f2937; }
.t-h { font-size: 15px; font-weight: 700; font-family: var(--slidev-code-font-family, monospace); }
.t-b { font-size: 14px; font-weight: 700; }
.t-m { font-size: 13px; font-weight: 700; }
.t-s { font-size: 12px; font-weight: 600; }
.t-xs { font-size: 11px; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; font-style: italic; }
.blue { fill: #4338ca; }
.net-t { fill: #1d4ed8; font-weight: 700; }
.gap-bg { fill: #fff; }
.gap-t { fill: #b91c1c; font-weight: 700; }
</style>
