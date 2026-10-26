<script setup lang="ts">
// eBPF = a safe in-kernel VM. Two phases: Load (verify + JIT a program) and Run
// (the attached hook reads/writes BPF maps, shared with user space). Minimal labels;
// the XDP/TC/kprobe specifics stay in the bullets.
</script>

<template>
  <svg class="vm" viewBox="0 0 700 280">
    <defs>
      <marker id="vm-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f2937" /></marker>
      <marker id="vm-s" viewBox="0 0 10 10" refX="2" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M10,0 L0,5 L10,10 z" fill="#1f2937" /></marker>
    </defs>

    <!-- Load phase -->
    <rect x="8" y="24" width="684" height="84" rx="10" class="grp" />
    <text x="24" y="44" class="t-cap">Load</text>
    <rect x="28" y="52" width="150" height="46" rx="7" class="end" />
    <text x="103" y="79" class="t-b" text-anchor="middle">restricted C</text>
    <path d="M178,75 H258" class="edge" marker-end="url(#vm-a)" />
    <text x="218" y="67" class="t-s muted" text-anchor="middle">bpf() syscall</text>
    <rect x="258" y="52" width="150" height="46" rx="7" class="bpf" />
    <text x="333" y="79" class="t-b" text-anchor="middle">Verifier</text>
    <path d="M408,75 H468" class="edge" marker-end="url(#vm-a)" />
    <rect x="468" y="52" width="160" height="46" rx="7" class="bpf" />
    <text x="548" y="79" class="t-b" text-anchor="middle">JIT → native</text>

    <!-- Run phase -->
    <rect x="8" y="180" width="684" height="92" rx="10" class="grp" />
    <!-- attach (drawn after the Run group so the group box doesn't hide it) -->
    <path d="M548,108 C548,160 115,150 115,204" class="edge" marker-end="url(#vm-a)" />
    <text x="380" y="138" class="t-s attach" text-anchor="middle">attach to hook</text>
    <text x="24" y="198" class="t-cap">Run</text>
    <rect x="40" y="206" width="150" height="46" rx="7" class="bpf" />
    <text x="115" y="233" class="t-b" text-anchor="middle">Kernel hook</text>
    <path d="M196,229 H268" class="edge" marker-start="url(#vm-s)" marker-end="url(#vm-a)" />
    <text x="232" y="221" class="t-s muted" text-anchor="middle">r/w</text>
    <rect x="272" y="206" width="138" height="46" rx="7" class="bpf" />
    <text x="341" y="233" class="t-b" text-anchor="middle">BPF maps</text>
    <path d="M416,229 H488" class="edge" marker-start="url(#vm-s)" marker-end="url(#vm-a)" />
    <rect x="492" y="206" width="168" height="46" rx="7" class="user" />
    <text x="576" y="227" class="t-b" text-anchor="middle">User space</text>
    <text x="576" y="243" class="t-s" text-anchor="middle">cilium-agent</text>
  </svg>
</template>

<style scoped>
.vm { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 400px; }
.grp { fill: #fcfdfc; stroke: #cbd5e1; stroke-dasharray: 5 4; }
.bpf  { fill: #dcf5dc; stroke: #374151; stroke-width: 1.4; }
.end  { fill: #f8fafc; stroke: #9ca3af; }
.user { fill: #e8eefc; stroke: #374151; stroke-width: 1.4; }
.edge { fill: none; stroke: #1f2937; stroke-width: 2; }
text { fill: #1f2937; }
.t-b { font-size: 13px; font-weight: 700; }
.t-s { font-size: 11px; }
.t-cap { font-size: 12px; font-weight: 700; fill: #6b7280; font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; }
.attach { fill: #6b7280; font-style: italic; }
</style>
