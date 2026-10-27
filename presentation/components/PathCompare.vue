<script setup lang="ts">
// Intra-node packet path, redrawn from fig:intranode in docs-latex/contents.tex.
// A looping "packet" stalls at each iptables hook and skims the eBPF steps (revealed on click).
// Steps ①–④ are the map lookups introduced on 1.5 (BpfMaps), same example Pods.
const props = withDefaults(defineProps<{ mode?: 'both' | 'calico' | 'cilium' }>(), { mode: 'both' })
const podA = 'Pod A eth0<br><code>frontend</code><br>10.0.1.5'
const podB = 'Pod B eth0<br><code>backend</code><br>10.0.1.9:8080'
const nf = [
  { t: podA, c: 'pod' },
  { t: 'veth<br>(cali*)', c: '' },
  { t: 'PREROUTING<br>(nat, conntrack)', c: 'nf' },
  { t: 'routing +<br>FORWARD<br>(policy chains)', c: 'nf' },
  { t: 'POSTROUTING', c: 'nf' },
  { t: 'veth', c: '' },
  { t: podB, c: 'pod' },
]
const steps = [
  { n: 'conntrack', ex: '.5 → .9:8080' },
  { n: 'ipcache', ex: '10.0.1.9 → 6789' },
  { n: 'policy map', ex: '12345 → :8080 ALLOW' },
  { n: 'endpoint map', ex: 'local → redirect' },
]
</script>

<template>
  <div class="paths" :class="{ single: props.mode !== 'both' }">
    <template v-if="props.mode !== 'cilium'"><div class="title">Calico · datapath iptables</div>
    <div class="row">
      <template v-for="(b, i) in nf" :key="i">
        <div class="arrow" v-if="i > 0" />
        <div class="box" :class="b.c" v-html="b.t" />
      </template>
      
    </div>
    </template><div v-if="props.mode !== 'calico'">
      <div class="title">Cilium eBPF host-routing</div>
      <div class="row">
        <div class="box pod" v-html="podA" />
        <div class="arrow fix" />
        <div class="box">veth<br>(lxc*)</div>
        <div class="arrow fix" />
        <div class="bpf-wrap">
          <div class="legend">eBPF @ TC ingress (<span class="mono">lxc*</span>) → <span class="mono">bpf_redirect_peer()</span></div>
          <template v-for="(s, i) in steps" :key="s.n">
            <div class="mini-arrow" v-if="i > 0" />
            <div class="step">
              <div class="sn"><span class="step-n">{{ i + 1 }}</span>{{ s.n }}</div>
              <div class="ex">{{ s.ex }}</div>
            </div>
          </template>
        </div>
        <div class="arrow fix" />
        <div class="box pod" v-html="podB" />
        
      </div>
    </div>
  </div>
</template>

<style scoped>
.single { padding: 64px 0 40px; }
.paths { font-size: 12px; line-height: 1.25; }
.title { font-weight: 700; text-align: center; margin: 6px 0 4px; }
.row { display: flex; align-items: center; position: relative; }
.box { border: 1px solid #374151; border-radius: 3px; padding: 6px 6px; text-align: center; background: #fff; min-width: 74px; }
.box.pod { background: #e8eefc; }
.box.nf { background: #ffe9cc; }
.arrow { flex: 1 0 18px; height: 2px; background: #1f2937; position: relative; margin: 0 2px; }
.arrow::after { content: ''; position: absolute; right: -1px; top: -4px; border-left: 7px solid #1f2937; border-top: 5px solid transparent; border-bottom: 5px solid transparent; }
.arrow.fix { flex: 0 0 26px; }
:deep(code) { font-size: 11px; }

/* eBPF program as a container of the 4 lookups; title sits on the border so the steps stay centred on the packet line. */
.bpf-wrap { flex: 1; display: flex; align-items: center; position: relative; background: #dcf5dc; border: 1px solid #374151; border-radius: 3px; padding: 14px 5px 8px; margin-top: 8px; }
.legend { position: absolute; top: -9px; left: 50%; transform: translateX(-50%); white-space: nowrap; background: #dcf5dc; border: 1px solid #374151; border-radius: 3px; padding: 0 6px; font-weight: 700; font-size: 11px; }
.mono { font-family: var(--slidev-code-font-family, monospace); font-size: 10.5px; }
.step { flex: 1 1 0; min-width: 0; background: #fff; border: 1px solid #374151; border-radius: 3px; padding: 4px 4px; text-align: center; }
.sn { display: flex; align-items: center; justify-content: center; gap: 4px; font-weight: 700; }
.ex { margin-top: 2px; font-family: var(--slidev-code-font-family, monospace); font-size: 9.5px; white-space: nowrap; color: #166534; }
.mini-arrow { flex: 0 0 12px; height: 2px; background: #1f2937; position: relative; margin: 0 2px; }
.mini-arrow::after { content: ''; position: absolute; right: -1px; top: -3px; border-left: 5px solid #1f2937; border-top: 4px solid transparent; border-bottom: 4px solid transparent; }

/* Both packets share a 6s loop, so the speed difference is visible side by side. */
.pkt { position: absolute; top: 50%; left: 2%; width: 13px; height: 13px; margin-top: -6.5px; border-radius: 50%; pointer-events: none; z-index: 1; }
.pkt.slow { background: #ea580c; box-shadow: 0 0 0 3px #fed7aa; animation: crawl 6s ease-in-out infinite; }
.pkt.fast { background: #16a34a; box-shadow: 0 0 0 3px #bbf7d0; animation: fly 6s ease-in-out infinite; }
@keyframes crawl {
  0% { left: 2%; opacity: 0; }
  4% { opacity: 1; }
  14%, 22% { left: 30%; }
  32%, 42% { left: 45%; }
  52%, 62% { left: 62%; }
  85% { left: 96%; opacity: 1; }
  92%, 100% { left: 96%; opacity: 0; }
}
/* Brief taps on steps ①–④, then straight into Pod B. */
@keyframes fly {
  0% { left: 2%; opacity: 0; }
  4% { opacity: 1; }
  9%, 11% { left: 31%; }
  14%, 16% { left: 46.5%; }
  19%, 21% { left: 62%; }
  24%, 26% { left: 78%; }
  32% { left: 96%; opacity: 1; }
  40%, 100% { left: 96%; opacity: 0; }
}
</style>
