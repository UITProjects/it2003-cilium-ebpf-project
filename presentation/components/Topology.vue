<script setup lang="ts">
// Cluster infrastructure, simplified from fig:topology in docs-latex/contents.tex: the two cluster subnets on one Proxmox host.
// Coordinates are in cm-like units; X()/Y() map them to px, PAD leaves room for the hypervisor frame.
const SX = 51
const SY = 56
const YMAX = 6.1
const PAD = 0.3
const X = (x: number) => (x + PAD) * SX
const Y = (y: number) => (YMAX - y) * SY
const W = (17 + 2 * PAD) * SX
const H = YMAX * SY

interface Box { x: number, y: number, w: number, h: number, cls: string, html: string }
const vms: Box[] = [
  { x: 1.55, y: 2.5, w: 120, h: 64, cls: 'cp', html: 'ubuntu2404-0<br>.40.160<br>control-plane' },
  { x: 4.25, y: 2.5, w: 120, h: 64, cls: 'vm', html: 'ubuntu2404-1<br>.40.161<br>worker' },
  { x: 6.95, y: 2.5, w: 120, h: 64, cls: 'vm', html: 'ubuntu2404-2<br>.40.162<br>worker' },
  { x: 10.05, y: 2.5, w: 136, h: 64, cls: 'cp', html: 'ubuntu2404-3<br>.50.160<br>control-plane, etcd' },
  { x: 12.75, y: 2.5, w: 120, h: 64, cls: 'vm', html: 'ubuntu2404-4<br>.50.161<br>worker' },
  { x: 15.45, y: 2.5, w: 120, h: 64, cls: 'vm', html: 'ubuntu2404-5<br>.50.162<br>worker' },
]
const busY = 3.9
const buses = [[1.55, 6.95], [10.05, 15.45]]

function rect(x1: number, y1: number, x2: number, y2: number) {
  return { left: `${X(x1)}px`, top: `${Y(y2)}px`, width: `${X(x2) - X(x1)}px`, height: `${Y(y1) - Y(y2)}px` }
}
function center(b: { x: number, y: number, w: number, h?: number }) {
  return { left: `${X(b.x) - b.w / 2}px`, top: `${Y(b.y) - (b.h ?? 0) / 2}px`, width: `${b.w}px`, height: b.h ? `${b.h}px` : undefined }
}
</script>

<template>
  <div class="topo" :style="{ width: `${W}px`, height: `${H}px` }">
    <!-- containers -->
    <div class="area pve" :style="rect(-PAD, 0, 17 + PAD, YMAX)" />
    <div class="label strong" :style="{ left: `${X(0.1)}px`, top: `${Y(6.02)}px` }">Proxmox VE hypervisor</div>
    <div class="area cilium" :style="rect(0.1, 0.3, 8.4, 5.3)" />
    <div class="area calico" :style="rect(8.6, 0.3, 16.9, 5.3)" />
    <div class="label center" :style="{ left: `${X(4.25) - 200}px`, width: '400px', top: `${Y(5.15)}px` }">
      <b>Cilium cluster</b><br><b>192.168.40.0/24</b> · gateway .1
    </div>
    <div class="label center" :style="{ left: `${X(12.75) - 200}px`, width: '400px', top: `${Y(5.15)}px` }">
      <b>Calico cluster</b><br><b>192.168.50.0/24</b> · gateway .1
    </div>
    <div class="label center" :style="{ left: `${X(4.25) - 200}px`, width: '400px', top: `${Y(1.15) - 14}px` }">
      kube-proxy replacement, direct routing<br>Hubble, LB pool .40.130–.40.150
    </div>
    <div class="label center" :style="{ left: `${X(12.75) - 200}px`, width: '400px', top: `${Y(1.15) - 14}px` }">
      Calico (BIRD BGP, direct routing)<br>kube-proxy mode iptables
    </div>

    <!-- wires -->
    <svg class="wires" :viewBox="`0 0 ${W} ${H}`" :width="W" :height="H">
      <line v-for="(b, i) in buses" :key="`bus${i}`" :x1="X(b[0])" :x2="X(b[1])" :y1="Y(busY)" :y2="Y(busY)" />
      <line v-for="(v, i) in vms" :key="`stub${i}`" :x1="X(v.x)" :x2="X(v.x)" :y1="Y(busY)" :y2="Y(v.y) - v.h / 2" />
    </svg>

    <!-- nodes -->
    <div v-for="(v, i) in vms" :key="`vm${i}`" class="box" :class="v.cls" :style="center(v)"><div v-html="v.html" /></div>
  </div>
</template>

<style scoped>
.topo { position: relative; font-size: 13px; line-height: 1.25; color: #1f2937; margin: 16px auto 0; }
.topo > * { position: absolute; }
.area { border-radius: 6px; }
.pve { border: 2px solid #374151; background: #f8f9fa; }
.cilium { border: 1px solid #4b5563; background: #eefbef; }
.calico { border: 1px solid #4b5563; background: #fff5ea; }
.label { white-space: nowrap; font-size: 14px; }
.label.center { text-align: center; }
.label.strong { font-weight: 700; }
.box { font-size: 12.5px; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; border: 1px solid #374151; border-radius: 3px; background: #fff; }
.box.cp { background: #e8eefc; }
.wires { left: 0; top: 0; overflow: visible; color: #1f2937; }
.wires line { stroke: currentColor; stroke-width: 1.6; fill: none; }
</style>
