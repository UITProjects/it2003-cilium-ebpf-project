<script setup lang="ts">
// Intra-node packet path, redrawn from fig:intranode in docs-latex/contents.tex.
// A looping "packet" stalls at each Netfilter hook and flies through the eBPF path (revealed on click).
const nf = [
  { t: 'Pod A<br>eth0', c: 'pod' },
  { t: 'veth<br>(cali*)', c: '' },
  { t: 'PREROUTING<br>(nat, conntrack)', c: 'nf' },
  { t: 'routing +<br>FORWARD<br>(policy chains)', c: 'nf' },
  { t: 'POSTROUTING', c: 'nf' },
  { t: 'veth', c: '' },
  { t: 'Pod B<br>eth0', c: 'pod' },
]
const bpf = [
  { t: 'Pod A<br>eth0', c: 'pod' },
  { t: 'veth<br>(lxc*)', c: '' },
  { t: 'eBPF @ TC ingress<br>map lookup + policy + <code>bpf_redirect_peer()</code>', c: 'bpf wide' },
  { t: 'Pod B<br>eth0', c: 'pod' },
]
</script>

<template>
  <div class="paths">
    <div class="title">iptables / Netfilter</div>
    <div class="row">
      <template v-for="(b, i) in nf" :key="i">
        <div class="arrow" v-if="i > 0" />
        <div class="box" :class="b.c" v-html="b.t" />
      </template>
      <div class="pkt slow" />
    </div>
    <div v-click>
      <div class="title">Cilium eBPF host-routing</div>
      <div class="row">
        <template v-for="(b, i) in bpf" :key="i">
          <div class="arrow" v-if="i > 0" />
          <div class="box" :class="b.c" v-html="b.t" />
        </template>
        <div class="pkt fast" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.paths { font-size: 12px; line-height: 1.25; }
.title { font-weight: 700; text-align: center; margin: 6px 0 4px; }
.row { display: flex; align-items: center; position: relative; }
.box { border: 1px solid #374151; border-radius: 3px; padding: 6px 6px; text-align: center; background: #fff; min-width: 74px; }
.box.pod { background: #e8eefc; }
.box.nf { background: #ffe9cc; }
.box.bpf { background: #dcf5dc; }
.box.wide { flex: 2; }
.arrow { flex: 1 0 18px; height: 2px; background: #1f2937; position: relative; margin: 0 2px; }
.arrow::after { content: ''; position: absolute; right: -1px; top: -4px; border-left: 7px solid #1f2937; border-top: 5px solid transparent; border-bottom: 5px solid transparent; }
:deep(code) { font-size: 11px; }

/* Both packets share a 6s loop, so the speed difference is visible side by side. */
.pkt { position: absolute; top: 50%; left: 2%; width: 13px; height: 13px; margin-top: -6.5px; border-radius: 50%; pointer-events: none; }
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
@keyframes fly {
  0% { left: 2%; opacity: 0; }
  4% { opacity: 1; }
  16%, 22% { left: 55%; }
  32% { left: 96%; opacity: 1; }
  40%, 100% { left: 96%; opacity: 0; }
}
</style>
