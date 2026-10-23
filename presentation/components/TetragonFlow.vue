<script setup lang="ts">
// E3 runtime security: after DVWA is exploited, the token read arrives two ways.
// Command Injection spawns a new process (easy to catch). File Inclusion reads the
// token inside the existing PHP worker — no new process — the blind spot of
// process monitoring, caught only by a file-access rule (security_file_permission).
// Signature animation: the LFI blind-spot box pulses gently (see .miss) to draw the eye.
</script>

<template>
  <svg class="tf" viewBox="0 0 660 288">
    <defs>
      <marker id="tf-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f2937" /></marker>
      <marker id="tf-ok" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#16a34a" /></marker>
      <marker id="tf-no" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#dc2626" /></marker>
    </defs>

    <!-- exploit entry -->
    <rect x="8" y="98" width="118" height="46" rx="7" class="infra" />
    <text x="67" y="126" class="t-b" text-anchor="middle">DVWA exploited</text>

    <!-- branch A: command injection = new process (caught by exec) -->
    <path d="M126,114 C148,100 162,80 180,78" class="edge n" marker-end="url(#tf-a)" />
    <rect x="62" y="24" width="186" height="52" rx="7" class="neutral" />
    <text x="155" y="44" class="t-b" text-anchor="middle">Command Injection</text>
    <text x="155" y="62" class="t-xs" text-anchor="middle">spawns sh / cat / curl · new process</text>
    <path d="M248,50 H300 V108" class="edge ok" marker-end="url(#tf-ok)" />
    <text x="320" y="46" class="t-xs mono muted" text-anchor="start">exec event</text>

    <!-- branch B: file inclusion = blind spot (no new process) -->
    <path d="M126,128 C148,148 162,176 182,186" class="edge n" marker-end="url(#tf-a)" />
    <rect x="46" y="186" width="200" height="56" rx="7" class="miss" />
    <text x="146" y="206" class="t-b" text-anchor="middle">File Inclusion (LFI)</text>
    <text x="146" y="223" class="t-xs" text-anchor="middle">read inside existing PHP worker</text>
    <text x="146" y="237" class="t-xs" text-anchor="middle">no new process</text>
    <path d="M246,214 H300 V150" class="edge ok" marker-end="url(#tf-ok)" />
    <text x="320" y="210" class="t-xs mono muted" text-anchor="start">file-read event</text>
    <text x="320" y="224" class="t-xs mono muted" text-anchor="start">security_file_permission</text>

    <!-- Tetragon engine -->
    <rect x="300" y="108" width="150" height="54" rx="7" class="infra" />
    <text x="375" y="130" class="t-b" text-anchor="middle">Tetragon</text>
    <text x="375" y="148" class="t-xs" text-anchor="middle">kprobe · tracepoint · LSM</text>

    <!-- captured: event + k8s context -->
    <path d="M450,122 H540" class="edge ok" marker-end="url(#tf-ok)" />
    <rect x="540" y="96" width="114" height="54" rx="7" class="ok" />
    <text x="597" y="118" class="t-b" text-anchor="middle">Event +</text>
    <text x="597" y="135" class="t-xs" text-anchor="middle">K8s context</text>

    <!-- optional enforcement (red dashed) -->
    <path d="M430,162 C470,186 500,200 540,204" class="edge no" marker-end="url(#tf-no)" />
    <text x="470" y="182" class="t-xs no-t" text-anchor="middle">enforce · Override -EPERM</text>
    <rect x="540" y="192" width="114" height="42" rx="7" class="deny" />
    <text x="597" y="217" class="t-b" text-anchor="middle">Deny token read</text>
  </svg>

  <div class="tf-legend">
    <span class="i"><i class="bx miss"></i> Điểm mù giám sát process (LFI)</span>
    <span class="i"><i class="ln ok"></i> Tetragon ghi nhận</span>
    <span class="i"><i class="ln no"></i> Enforce: từ chối (tùy chọn)</span>
  </div>
</template>

<style scoped>
.tf { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 300px; }
.infra   { fill: #e8eefc; stroke: #374151; stroke-width: 1.4; }
.neutral { fill: #f8fafc; stroke: #9ca3af; }
.miss { fill: #ffe9cc; stroke: #d97706; stroke-width: 1.6; animation: pulse 2.6s ease-in-out infinite; }
.ok   { fill: #dcf5dc; stroke: #16a34a; stroke-width: 1.4; }
.deny { fill: #ffd0d0; stroke: #dc2626; stroke-width: 1.6; }
.edge { fill: none; stroke-width: 2.1; }
.edge.n  { stroke: #1f2937; }
.edge.ok { stroke: #16a34a; }
.edge.no { stroke: #dc2626; stroke-dasharray: 6 4; }
text { fill: #1f2937; }
.t-b { font-size: 12.5px; font-weight: 700; }
.t-xs { font-size: 10.5px; }
.no-t { fill: #dc2626; font-weight: 700; }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; }
@keyframes pulse { 0%, 100% { stroke-width: 1.6; } 50% { stroke-width: 3; } }

.tf-legend { display: flex; justify-content: center; flex-wrap: wrap; gap: 1.3rem; font-size: 0.8rem; margin-top: 0.5rem; }
.tf-legend .i { display: inline-flex; align-items: center; gap: 0.4rem; }
.tf-legend .ln { width: 22px; height: 0; border-top: 3px solid; display: inline-block; }
.tf-legend .ln.ok { border-color: #16a34a; }
.tf-legend .ln.no { border-color: #dc2626; border-top-style: dashed; }
.tf-legend .bx { width: 13px; height: 13px; border-radius: 3px; border: 1px solid; display: inline-block; }
.tf-legend .bx.miss { background: #ffe9cc; border-color: #d97706; }
</style>
