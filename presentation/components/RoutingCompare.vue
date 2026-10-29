<script setup lang="ts">
// Slide 2.1.2 (E1): the E1 request path across nodes (fortio client on one worker → ClusterIP → server on the other).
// Calico: the packet climbs the host network stack (Netfilter + routing) on both nodes.
// Cilium (BPF host routing): TC programs forward it with bpf_redirect_neigh / bpf_redirect_peer, so the
// host stack is bypassed and the packet lands straight in the server Pod's netns.
// One CSS grid for both lanes so the node columns line up; node backgrounds span every row.
const nf1 = ['PREROUTING · DNAT<br><span class="mono">KUBE-SERVICES</span> O(n)', 'routing (FIB)', 'FORWARD (policy)', 'POSTROUTING']
const nf2 = ['PREROUTING', 'routing (FIB)', 'FORWARD (policy)', 'POSTROUTING']
const bpf1 = ['policy · conntrack', '<span class="mono">bpf_fib_lookup()</span>', '<span class="mono">bpf_redirect_neigh()</span> → eth0']
const bpf2 = ['policy · conntrack', '<span class="mono">bpf_redirect_peer()</span> → Pod eth0']
</script>

<template>
  <div class="rc">
    <div class="node n1" />
    <div class="node n2" />
    <div class="nh h1">Node 1 · <span class="mono">10.244.1.0/24</span> · fortio client</div>
    <div class="nh hw">L2<br>no encap</div>
    <div class="nh h2">Node 2 · <span class="mono">10.244.2.0/24</span> · fortio server</div>

    <!-- Calico / iptables -->
    <div class="lane l1">Calico · kube-proxy iptables</div>
    <div class="box pod r1 c1">client<br>Pod</div>
    <div class="arrow r1 c2" />
    <div class="box dim r1 c3 mono">cali*</div>
    <div class="arrow r1 c4" />
    <div class="grp nf r1 c5">
      <div class="gt">host network stack</div>
      <div v-for="s in nf1" :key="s" class="it" v-html="s" />
    </div>
    <div class="arrow r1 c6" />
    <div class="box nic r1 c7 mono">eth0</div>
    <div class="wire r1 c8" />
    <div class="box nic r1 c9 mono">eth0</div>
    <div class="arrow r1 c10" />
    <div class="grp nf r1 c11">
      <div class="gt">host network stack</div>
      <div v-for="s in nf2" :key="s" class="it" v-html="s" />
    </div>
    <div class="arrow r1 c12" />
    <div class="box dim r1 c13 mono">cali*</div>
    <div class="arrow r1 c14" />
    <div class="box pod r1 c15">server<br>Pod</div>

    <!-- Cilium / eBPF -->
    <div class="lane l2">Cilium · eBPF host routing</div>
    <div class="box pod r2 c1">client<br>Pod</div>
    <div class="arrow r2 c2" />
    <div class="box dim r2 c3 mono">lxc*</div>
    <div class="arrow r2 c4" />
    <div class="grp bpf r2 c5">
      <div class="gt">eBPF @ TC (<span class="mono">lxc*</span>)</div>
      <div v-for="s in bpf1" :key="s" class="it" v-html="s" />
    </div>
    <div class="arrow r2 c6" />
    <div class="box nic r2 c7 mono">eth0</div>
    <div class="wire r2 c8" />
    <div class="box nic r2 c9 mono">eth0</div>
    <div class="arrow r2 c10" />
    <div class="grp bpf r2 c11s">
      <div class="gt">eBPF @ TC ingress (<span class="mono">eth0</span>)</div>
      <div v-for="s in bpf2" :key="s" class="it" v-html="s" />
    </div>
    <div class="arrow r2 c14" />
    <div class="box pod r2 c15">server<br>Pod</div>

    <div class="tag r3 c1to3">Service → backend:<br>LB map O(1)</div>
    <div class="skip r3 c5"><s>Netfilter · host routing</s> bypassed</div>
    <div class="skip r3 c11s"><s>Netfilter · host routing · <span class="mono">lxc*</span></s> bypassed</div>

    <div class="legend">
      <span class="i"><i class="bx nf" /> Netfilter / routing in host stack</span>
      <span class="i"><i class="bx bpf" /> eBPF program at TC</span>
      <span class="i"><i class="bx skip" /> bypassed</span>
    </div>
  </div>
</template>

<style scoped>
.rc {
  display: grid; color: #1f2937; font-size: 12px; line-height: 1.2; column-gap: 0; row-gap: 4px;
  grid-template-columns: 70px 18px 50px 18px 1fr 18px 46px 84px 46px 18px 1fr 18px 50px 18px 70px;
  grid-template-rows: auto auto auto auto auto auto;
}
.mono { font-family: var(--slidev-code-font-family, monospace); }
:deep(.mono) { font-family: var(--slidev-code-font-family, monospace); font-size: 10.5px; }

/* node backgrounds behind both lanes */
.node { grid-row: 1 / 7; background: #f8fafc; border: 1.5px solid #374151; border-radius: 8px; margin: 0 -8px; }
.n1 { grid-column: 1 / 8; }
.n2 { grid-column: 9 / 16; }
.nh { grid-row: 1; font-weight: 700; font-size: 13px; padding: 6px 0 0; z-index: 1; }
.h1 { grid-column: 1 / 8; }
.h2 { grid-column: 9 / 16; }
.hw { grid-column: 8; text-align: center; font-size: 10.5px; font-weight: 400; color: #6b7280; padding-top: 6px; line-height: 1.15; }

.lane { grid-column: 1 / 16; justify-self: center; background: #fff; border: 1px solid #374151; border-radius: 12px; padding: 1px 12px; text-align: center; font-weight: 700; font-size: 13.5px; z-index: 1; font-family: var(--slidev-code-font-family, monospace); }
.l1 { grid-row: 2; }
.l2 { grid-row: 4; margin-top: 2px; }
.r1 { grid-row: 3; }
.r2 { grid-row: 5; }
.r3 { grid-row: 6; margin-bottom: 6px; }
.c1 { grid-column: 1; } .c2 { grid-column: 2; } .c3 { grid-column: 3; } .c4 { grid-column: 4; }
.c5 { grid-column: 5; } .c6 { grid-column: 6; } .c7 { grid-column: 7; } .c8 { grid-column: 8; }
.c9 { grid-column: 9; } .c10 { grid-column: 10; } .c11 { grid-column: 11; } .c12 { grid-column: 12; }
.c13 { grid-column: 13; } .c14 { grid-column: 14; } .c15 { grid-column: 15; }
.c11s { grid-column: 11 / 14; }
.c1to3 { grid-column: 1 / 4; }

.box, .grp, .arrow, .wire, .tag, .skip { z-index: 1; }
.box { align-self: center; border: 1px solid #374151; border-radius: 4px; padding: 6px 4px; text-align: center; background: #fff; }
.box.pod { background: #e8eefc; font-weight: 700; }
.box.dim { border-color: #9ca3af; color: #6b7280; font-size: 11px; }
.box.nic { font-size: 11px; }

.grp { border: 1px solid #374151; border-radius: 6px; padding: 4px 6px 6px; }
.grp.nf { background: #ffe9cc; align-self: center; }
.grp.bpf { background: #dcf5dc; align-self: center; }
.gt { font-weight: 700; text-align: center; font-size: 11.5px; margin-bottom: 3px; }
.it { background: #fff; border: 1px solid #374151; border-radius: 3px; padding: 1px 4px; margin-top: 3px; text-align: center; font-size: 11px; }
.nf .it:first-of-type { margin-top: 0; }

.arrow { align-self: center; height: 2px; background: #1f2937; position: relative; margin: 0 3px; }
.arrow::after { content: ''; position: absolute; right: -1px; top: -4px; border-left: 7px solid #1f2937; border-top: 5px solid transparent; border-bottom: 5px solid transparent; }
.wire { align-self: center; height: 4px; background: #374151; position: relative; margin: 0 2px; }
.wire::after { content: ''; position: absolute; right: -2px; top: -4px; border-left: 8px solid #374151; border-top: 6px solid transparent; border-bottom: 6px solid transparent; }

.tag { align-self: start; text-align: center; font-size: 10.5px; color: #166534; background: #dcf5dc; border: 1px dashed #15803d; border-radius: 4px; padding: 2px 3px; margin-right: 6px; }
.skip { align-self: start; text-align: center; font-size: 10.5px; color: #6b7280; border: 1.2px dashed #9ca3af; border-radius: 4px; padding: 3px 4px; }
.skip s { text-decoration-color: #9ca3af; }

.legend { grid-column: 1 / 16; grid-row: 7; display: flex; justify-content: center; gap: 1.4rem; font-size: 0.78rem; margin-top: 6px; }
.legend .i { display: inline-flex; align-items: center; gap: 0.4rem; }
.legend .bx { width: 13px; height: 13px; border-radius: 3px; border: 1px solid #374151; display: inline-block; }
.legend .bx.nf { background: #ffe9cc; }
.legend .bx.bpf { background: #dcf5dc; }
.legend .bx.skip { background: #fff; border: 1.2px dashed #9ca3af; }
</style>
