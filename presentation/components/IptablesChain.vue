<script setup lang="ts">
// Slide 1.2: iptables = a chain of rules matched one by one (generic chain; KUBE-SERVICES itself is on 2.1.1). The first packet (SYN) walks
// the chain until a rule matches, then DNAT; conntrack stores that decision so the next
// packets of the same connection skip the chain. Netfilter hook detail lives in the notes.
</script>

<template>
  <svg class="ic" viewBox="0 0 860 300">
    <defs>
      <marker id="ic-a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f2937" /></marker>
      <marker id="ic-g" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#6b7280" /></marker>
    </defs>

    <!-- lane 1: first packet walks the chain -->
    <rect x="12" y="74" width="100" height="48" rx="7" class="end" />
    <text x="62" y="95" class="t-b" text-anchor="middle">1st packet</text>
    <text x="62" y="111" class="t-s muted" text-anchor="middle">SYN</text>

    <rect x="140" y="30" width="400" height="128" rx="10" class="grp" />
    <text x="154" y="50" class="t-cap">chain · table nat</text>
    <path d="M112,98 H160" class="edge" marker-end="url(#ic-a)" />

    <rect x="160" y="74" width="86" height="48" rx="7" class="rule" />
    <text x="203" y="95" class="t-b" text-anchor="middle">rule 1</text>
    <text x="203" y="112" class="t-s no" text-anchor="middle">✗ no match</text>
    <path d="M246,98 H264" class="edge" marker-end="url(#ic-a)" />
    <rect x="264" y="74" width="86" height="48" rx="7" class="rule" />
    <text x="307" y="95" class="t-b" text-anchor="middle">rule 2</text>
    <text x="307" y="112" class="t-s no" text-anchor="middle">✗ no match</text>
    <path d="M350,98 H368" class="edge" marker-end="url(#ic-a)" />
    <text x="388" y="103" class="t-b" text-anchor="middle">…</text>
    <path d="M404,98 H422" class="edge" marker-end="url(#ic-a)" />
    <rect x="422" y="74" width="98" height="48" rx="7" class="rule hit" />
    <text x="471" y="95" class="t-b" text-anchor="middle">rule n</text>
    <text x="471" y="112" class="t-s yes" text-anchor="middle">✓ match</text>
    <text x="340" y="146" class="t-b" text-anchor="middle">sequential match · O(n) rules</text>

    <path d="M520,98 H580" class="edge" marker-end="url(#ic-a)" />
    <rect x="580" y="74" width="92" height="48" rx="7" class="plain" />
    <text x="626" y="95" class="t-b" text-anchor="middle">DNAT</text>
    <text x="626" y="111" class="t-s mono" text-anchor="middle">→ Pod IP</text>
    <path d="M672,98 H716" class="edge" marker-end="url(#ic-a)" />

    <!-- first packet stores its NAT decision in conntrack -->
    <path d="M626,122 V196 H300 V222" class="edge save" marker-end="url(#ic-g)" />
    <text x="470" y="190" class="t-s muted" text-anchor="middle">store NAT decision</text>

    <!-- lane 2: next packets hit conntrack and skip the chain -->
    <rect x="12" y="224" width="100" height="48" rx="7" class="end" />
    <text x="62" y="245" class="t-b" text-anchor="middle">next packets</text>
    <text x="62" y="261" class="t-s muted" text-anchor="middle">same connection</text>
    <path d="M112,248 H220" class="edge" marker-end="url(#ic-a)" />
    <rect x="220" y="224" width="160" height="48" rx="7" class="ct" />
    <text x="300" y="245" class="t-b" text-anchor="middle">conntrack hit</text>
    <text x="300" y="261" class="t-s" text-anchor="middle">reuse NAT · O(1)</text>
    <path d="M380,248 H716" class="edge" marker-end="url(#ic-a)" />
    <text x="548" y="240" class="t-s muted" text-anchor="middle">skips the chain</text>

    <!-- destination -->
    <rect x="716" y="74" width="132" height="198" rx="7" class="pod" />
    <text x="782" y="168" class="t-b muted" text-anchor="middle">backend Pod</text>
    <text x="782" y="186" class="t-s mono muted" text-anchor="middle">10.244.1.20</text>
  </svg>

  <div class="ic-legend">
    <span class="i"><i class="bx rule"></i> iptables rule</span>
    <span class="i"><b class="no">✗</b> no match → next rule</span>
    <span class="i"><b class="yes">✓</b> match → jump / target</span>
    <span class="i"><i class="ln"></i> conntrack entry written</span>
  </div>
</template>

<style scoped>
.ic { width: 100%; height: auto; display: block; margin: 0 auto; max-height: 380px; }
.grp  { fill: #fcfdfc; stroke: #cbd5e1; stroke-dasharray: 5 4; }
.rule { fill: #ffe9cc; stroke: #374151; stroke-width: 1.4; }
.rule.hit { stroke-width: 2.4; }
.ct   { fill: #e8eefc; stroke: #374151; stroke-width: 1.4; }
.pod  { fill: #fafafa; stroke: #9ca3af; }
.plain { fill: #fff; stroke: #9ca3af; stroke-width: 1.4; }
.end  { fill: #f8fafc; stroke: #9ca3af; }
.edge { fill: none; stroke: #1f2937; stroke-width: 2; }
.edge.save { stroke: #6b7280; stroke-dasharray: 6 4; }
text { fill: #1f2937; }
.t-b { font-size: 13px; font-weight: 700; }
.t-s { font-size: 11px; }
.t-cap { font-size: 12px; font-weight: 700; fill: #6b7280; font-family: var(--slidev-code-font-family, monospace); }
.mono { font-family: var(--slidev-code-font-family, monospace); }
.muted { fill: #6b7280; }
text.no { fill: #dc2626; font-weight: 700; }
text.yes { fill: #16a34a; font-weight: 700; }

.ic-legend { display: flex; justify-content: center; flex-wrap: wrap; gap: 1.3rem; font-size: 0.8rem; margin-top: 0.5rem; }
.ic-legend .i { display: inline-flex; align-items: center; gap: 0.4rem; }
.ic-legend .no { color: #dc2626; }
.ic-legend .yes { color: #16a34a; }
.ic-legend .bx { width: 13px; height: 13px; border-radius: 3px; border: 1px solid #374151; display: inline-block; }
.ic-legend .bx.rule { background: #ffe9cc; }
.ic-legend .ln { width: 22px; height: 0; border-top: 3px dashed #6b7280; display: inline-block; }
</style>
