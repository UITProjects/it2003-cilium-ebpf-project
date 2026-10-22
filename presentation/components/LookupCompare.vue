<script setup lang="ts">
// Service lookup, redrawn from fig:lookup in docs-latex/contents.tex.
// Animated on a shared 5s loop: iptables scans rule by rule before matching, the hash map hits at once.
const rules = ['rule 1: svc-1', 'rule 2: svc-2', 'rule 3: svc-3']
const buckets = ['bucket 0', 'bucket 1', 'bucket k: svc-n', '⋮', 'bucket m']
</script>

<template>
  <div class="lookup">
    <div class="side">
      <div class="title">iptables: KUBE-SERVICES</div>
      <div class="chain">
        <template v-for="(r, i) in rules" :key="r">
          <div class="rule scan" :style="{ animationDelay: `${0.5 + i * 0.5}s` }">{{ r }}</div>
          <div class="down" />
        </template>
        <div class="dots scan-dots">⋮</div>
        <div class="down" />
        <div class="rule hit match">rule n: svc-n (match)</div>
      </div>
      <div class="caption">linear rule scan: <b>O(n)</b></div>
    </div>
    <div class="side">
      <div class="title">eBPF: cilium_lb4_services_v2</div>
      <div class="hash">
        <div class="key">hash(VIP, port, proto)</div>
        <div class="right" />
        <div class="map">
          <div v-for="b in buckets" :key="b" :class="b === '⋮' ? 'dots' : ['bucket', { 'hit bucket-hit': b.startsWith('bucket k') }]">{{ b }}</div>
        </div>
      </div>
      <div class="caption">hash map lookup: <b>O(1)</b></div>
    </div>
  </div>
</template>

<style scoped>
.lookup { display: flex; gap: 80px; justify-content: center; font-size: 13.5px; }
.side { display: flex; flex-direction: column; align-items: center; }
.title { font-weight: 700; font-size: 15px; margin-bottom: 6px; font-family: var(--slidev-code-font-family, monospace); }
.chain { display: flex; flex-direction: column; align-items: center; }
.rule, .bucket, .key { font-family: var(--slidev-code-font-family, monospace); border: 1px solid #374151; padding: 4px 10px; text-align: center; }
.rule { background: #ffe9cc; width: 230px; }
.bucket { background: #dcf5dc; width: 200px; margin-bottom: 5px; }
.hit { background: #ffd0d0; font-weight: 700; }
.key { background: #e8eefc; }
.down { width: 2px; height: 11px; background: #1f2937; position: relative; }
.down::after { content: ''; position: absolute; bottom: -5px; left: -4px; border-top: 6px solid #1f2937; border-left: 5px solid transparent; border-right: 5px solid transparent; }
.dots { line-height: 1; margin: 2px 0; text-align: center; }
.hash { display: flex; align-items: center; flex: 1; }
.right { width: 44px; height: 2px; background: #1f2937; position: relative; margin-right: 6px; }
.right::after { content: ''; position: absolute; right: -2px; top: -4px; border-left: 7px solid #1f2937; border-top: 5px solid transparent; border-bottom: 5px solid transparent; }
.caption { margin-top: 10px; font-size: 16px; }

/* iptables: each rule lights up in turn, the match lands late. */
.scan { animation: scan 5s infinite both; }
@keyframes scan {
  0%, 8% { background: #fde047; transform: scale(1.06); }
  10%, 100% { background: #ffe9cc; transform: scale(1); }
}
.scan-dots { animation: blink 5s 2s infinite both; }
@keyframes blink { 0%, 8% { color: #ca8a04; transform: scale(1.6); } 10%, 100% { color: inherit; transform: scale(1); } }
.match { animation: match 5s infinite; }
@keyframes match {
  0%, 52% { background: #ffe9cc; font-weight: 400; transform: scale(1); }
  55%, 92% { background: #fca5a5; font-weight: 700; transform: scale(1.08); }
  100% { background: #ffe9cc; transform: scale(1); }
}
/* eBPF: one hop, immediate hit. */
.key { animation: key 5s infinite; }
@keyframes key { 0%, 6% { box-shadow: 0 0 0 4px #93c5fd; } 10%, 100% { box-shadow: none; } }
.bucket-hit { animation: bhit 5s infinite; }
@keyframes bhit {
  0%, 8% { background: #dcf5dc; font-weight: 400; transform: scale(1); }
  10%, 92% { background: #fca5a5; font-weight: 700; transform: scale(1.08); }
  100% { background: #dcf5dc; transform: scale(1); }
}
</style>
