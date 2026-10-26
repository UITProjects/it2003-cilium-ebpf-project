<script setup lang="ts">
// Homelab topology, redrawn from fig:topology in docs-latex/contents.tex.
// Coordinates are the TikZ ones (cm); X()/Y() map them to px so the layout stays identical.
// Clicks walk through the parts: 1 remote access path, 2 Cilium cluster, 3 Calico cluster, 4 isolation, 5 all again.
import { computed } from 'vue'
import { useSlideContext } from '@slidev/client'

const { $clicks } = useSlideContext()
const focus = computed(() => ['', 'access', 'cilium', 'calico', 'fw', ''][$clicks.value] ?? '')
const SX = 52
const SY = 34
const YMAX = 8.6
const X = (x: number) => x * SX
const Y = (y: number) => (YMAX - y) * SY
const W = 17 * SX
const H = YMAX * SY

interface Box { x: number, y: number, w: number, h: number, cls: string, html: string, g: string }
const vms: Box[] = [
  { x: 1.65, y: 2.6, w: 94, h: 46, cls: 'vpn', html: 'vpn-server<br>.40.10<br>OpenVPN', g: 'cilium access' },
  { x: 3.6, y: 2.6, w: 94, h: 46, cls: 'cp', g: 'cilium', html: 'ubuntu2404-0<br>.40.160<br>control-plane' },
  { x: 5.5, y: 2.6, w: 94, h: 46, cls: 'vm', g: 'cilium', html: 'ubuntu2404-1<br>.40.161<br>worker' },
  { x: 7.35, y: 2.6, w: 94, h: 46, cls: 'vm', g: 'cilium', html: 'ubuntu2404-2<br>.40.162<br>worker' },
  { x: 10.2, y: 2.6, w: 104, h: 46, cls: 'cp', g: 'calico', html: 'ubuntu2404-3<br>.50.160<br>control-plane, etcd' },
  { x: 12.55, y: 2.6, w: 94, h: 46, cls: 'vm', g: 'calico', html: 'ubuntu2404-4<br>.50.161<br>worker' },
  { x: 14.9, y: 2.6, w: 94, h: 46, cls: 'vm', g: 'calico', html: 'ubuntu2404-5<br>.50.162<br>worker' },
]
const busY = 4.3
const buses = [[0.95, 7.35, 'cilium'], [10.2, 16.05, 'calico']] as const

function rect(x1: number, y1: number, x2: number, y2: number) {
  return { left: `${X(x1)}px`, top: `${Y(y2)}px`, width: `${X(x2) - X(x1)}px`, height: `${Y(y1) - Y(y2)}px` }
}
function center(b: { x: number, y: number, w: number, h?: number }) {
  return { left: `${X(b.x) - b.w / 2}px`, top: `${Y(b.y) - (b.h ?? 0) / 2}px`, width: `${b.w}px`, height: b.h ? `${b.h}px` : undefined }
}
const P = (pts: number[][]) => pts.map(([x, y]) => `${X(x)},${Y(y)}`).join(' ')
</script>

<template>
  <div class="topo" :data-f="focus" :style="{ width: `${W}px`, height: `${H}px` }">
    <!-- containers -->
    <div class="area pve" :style="rect(0, 0, 17, 8.4)" />
    <div class="label strong" :style="{ left: `${X(0.2)}px`, top: `${Y(8.3)}px` }">Proxmox VE: pve-master (192.168.1.120)</div>
    <div class="area sdn" :style="rect(0.3, 0.3, 16.7, 6.3)" />
    <div class="label italic center" :style="{ left: `${X(8.5) - 150}px`, width: '300px', top: `${Y(6.25)}px` }">SDN simple zone <code>it2003</code> (MTU 1500)</div>
    <div class="area cilium" data-g="cilium" :style="rect(0.6, 0.6, 8.3, 5.6)" />
    <div class="area calico" data-g="calico" :style="rect(8.7, 0.6, 16.4, 5.6)" />
    <div class="label center" data-g="cilium" :style="{ left: `${X(4.45) - 200}px`, width: '400px', top: `${Y(5.5)}px` }">
      <b>VNet it2003: 192.168.40.0/24</b><br>gateway .1 (SNAT on host) – <b>Cilium cluster</b>
    </div>
    <div class="label center" data-g="calico" :style="{ left: `${X(12.55) - 200}px`, width: '400px', top: `${Y(5.5)}px` }">
      <b>VNet it2003b: 192.168.50.0/24</b><br>gateway .1 (SNAT on host) – <b>Calico cluster</b>
    </div>
    <div class="label center" data-g="cilium" :style="{ left: `${X(4.45) - 200}px`, width: '400px', top: `${Y(1.15) - 14}px` }">
      Cilium 1.20.1, kube-proxy replacement, direct routing<br>Hubble, LB pool .40.130–.40.150 (L2 announcement)
    </div>
    <div class="label center" data-g="calico" :style="{ left: `${X(12.55) - 200}px`, width: '400px', top: `${Y(1.15) - 14}px` }">
      Calico (BIRD BGP, direct routing)<br>kube-proxy mode iptables
    </div>

    <!-- wires -->
    <svg class="wires" :viewBox="`0 0 ${W} ${H}`" :width="W" :height="H">
      <defs>
        <marker id="topo-arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" fill="currentColor" />
        </marker>
      </defs>
      <line v-for="(b, i) in buses" :key="`bus${i}`" :data-g="b[2]" :x1="X(b[0])" :x2="X(b[1])" :y1="Y(busY)" :y2="Y(busY)" />
      <line v-for="(v, i) in vms" :key="`stub${i}`" :data-g="v.g" :x1="X(v.x)" :x2="X(v.x)" :y1="Y(busY)" :y2="Y(v.y) - v.h / 2" />
      <polyline data-g="cilium access" :points="P([[0.95, 4.3], [0.95, 6.55], [7.6, 6.55], [7.6, 6.85]])" />
      <polyline data-g="calico access" :points="P([[16.05, 4.3], [16.05, 6.55], [9.4, 6.55], [9.4, 6.85]])" />
    </svg>

    <!-- nodes -->
    <div v-for="(v, i) in vms" :key="`vm${i}`" class="box" :class="v.cls" :data-g="v.g" :style="center(v)"><div v-html="v.html" /></div>
    <div class="box ext" data-g="access" :style="center({ x: 8.5, y: 7.3, w: 300, h: 34 })">
      <div><b>vmbr0</b> + iptables DNAT<br>SSH 2160–2165, K8s API 2443/2444, OpenVPN 2194/udp</div>
    </div>
    <div class="label fw" data-g="fw" :style="{ left: `${X(16.8) - 250}px`, width: '250px', top: `${Y(7.3) - 22}px` }">
      Proxmox firewall (per VM):<br>OUT → 192.168.1.0/24: DROP<br>(VPN server → 192.168.1.2: allow)
    </div>
  </div>
</template>

<style scoped>
.topo { position: relative; font-size: 10px; line-height: 1.2; color: #1f2937; margin: 0 auto; }
.topo > * { position: absolute; }
.area { border-radius: 6px; }
.pve { border: 2px solid #374151; background: #f8f9fa; }
.sdn { border: 1.5px dashed #6b7280; }
.cilium { border: 1px solid #4b5563; background: #eefbef; }
.calico { border: 1px solid #4b5563; background: #fff5ea; }
.label { white-space: nowrap; }
.label.center { text-align: center; }
.label.strong { font-weight: 700; font-size: 12px; }
.label.italic { font-style: italic; }
.fw { color: #9f1d1d; white-space: normal; }
.box { display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; border: 1px solid #374151; border-radius: 3px; background: #fff; }
.box.cp { background: #e8eefc; }
.box.vpn { background: #fdf6cc; }
.box.ext { background: #f1f3f5; border-radius: 5px; }
.box.router { background: #e6f7fa; }
.wires { left: 0; top: 0; overflow: visible; color: #1f2937; }
.wires line, .wires polyline { stroke: currentColor; stroke-width: 1.6; fill: none; }
.wires text { font-size: 8.5px; fill: currentColor; }
code { font-size: 9px; padding: 0 2px; }

/* Click-driven focus: tagged parts outside the focused group fade, the focused group glows. */
[data-g] { transition: opacity 0.45s ease, box-shadow 0.45s ease, transform 0.45s ease; }
.topo[data-f='access'] [data-g]:not([data-g~='access']),
.topo[data-f='cilium'] [data-g]:not([data-g~='cilium']),
.topo[data-f='calico'] [data-g]:not([data-g~='calico']),
.topo[data-f='fw'] [data-g]:not([data-g~='fw']) { opacity: 0.18; }
.topo[data-f='access'] .box[data-g~='access'] { box-shadow: 0 0 0 3px #38bdf8; }
.topo[data-f='cilium'] .area.cilium { box-shadow: 0 0 0 4px #22c55e, 0 0 18px #86efac; }
.topo[data-f='calico'] .area.calico { box-shadow: 0 0 0 4px #f97316, 0 0 18px #fdba74; }
.topo[data-f='fw'] .fw { transform: scale(1.08); transform-origin: right center; font-weight: 700; }
.topo[data-f='access'] .wires .flow { stroke: #0284c7; stroke-width: 2.4; stroke-dasharray: 7 5; animation: flow 0.9s linear infinite; }
@keyframes flow { to { stroke-dashoffset: -12; } }
</style>
