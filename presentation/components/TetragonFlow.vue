<template>
  <svg class="tf" viewBox="0 0 900 265" role="img" aria-label="Ba bước: ghi nhận process, điểm mù File Inclusion, bổ sung rule file">
    <defs><marker id="tf-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#94a3b8" /></marker></defs>
    <line x1="300" y1="20" x2="300" y2="224" class="divider" />
    <line x1="600" y1="20" x2="600" y2="224" class="divider" />
    <text x="20" y="34" class="number">01</text>
    <text x="64" y="34" class="title">Command Injection</text>
    <text x="20" y="67" class="body">Lệnh đọc ca.crt / token</text>
    <path d="M30,79 V103" class="arrow" />
    <text x="20" y="124" class="body bold">Sinh process mới</text>
    <text x="20" y="146" class="detail">shell / công cụ đọc file</text>
    <path d="M30,158 V181" class="arrow" />
    <circle cx="28" cy="204" r="8" class="green-dot" />
    <path d="M24,204 L27,207 L32,201" class="check" />
    <text x="46" y="208" class="result green">Ghi nhận process_exec</text>
    <text x="20" y="230" class="detail">Chưa có sự kiện đọc file riêng</text>
    <text x="320" y="34" class="number amber">02</text>
    <text x="364" y="34" class="title">File Inclusion</text>
    <text x="320" y="67" class="body">Upload PHP → include file</text>
    <path d="M330,79 V103" class="arrow" />
    <text x="320" y="124" class="body bold">PHP worker đọc trực tiếp</text>
    <text x="320" y="146" class="detail">Payload không sinh process mới</text>
    <path d="M330,158 V181" class="arrow" />
    <circle cx="328" cy="204" r="8" class="amber-dot" />
    <text x="328" y="208" class="bang" text-anchor="middle">!</text>
    <text x="346" y="208" class="result amber">Bỏ sót thao tác đọc file</text>
    <text x="320" y="230" class="detail">Khi chỉ giám sát process</text>
    <text x="620" y="34" class="number">03</text>
    <text x="664" y="34" class="title">Thêm rule file</text>
    <text x="620" y="67" class="body">Lặp lại cùng request LFI</text>
    <path d="M630,79 V103" class="arrow" />
    <text x="620" y="124" class="body bold">kprobe theo dõi đọc file</text>
    <text x="620" y="146" class="mono">security_file_permission</text>
    <path d="M630,158 V181" class="arrow" />
    <circle cx="628" cy="204" r="8" class="green-dot" />
    <path d="M624,204 L627,207 L632,201" class="check" />
    <text x="646" y="208" class="result green">Phát hiện file-access event</text>
    <text x="620" y="230" class="detail">Đường dẫn + PHP worker + Pod</text>
    <text x="450" y="261" class="footer" text-anchor="middle">TETRAGON · MONITOR ONLY · GHI NHẬN SỰ KIỆN</text>
  </svg>
</template>
<style scoped>
.tf { width:100%; height:auto; display:block; margin:12px auto 0; max-height:300px; }
text { font-family:var(--slidev-font-sans); fill:#243447; }
.title { font-size:16px; font-weight:700; }
.number { font-size:22px; font-weight:700; fill:#15803d; }
.body { font-size:14px; }
.bold { font-weight:600; }
.detail { font-size:11.8px; fill:#64748b; }
.mono { font-size:11.5px; fill:#64748b; font-family:var(--slidev-code-font-family,monospace); }
.result { font-size:13px; font-weight:700; }
.green { fill:#15803d; }
.amber { fill:#b45309; }
.divider { stroke:#e2e8f0; stroke-width:1; }
.arrow { fill:none; stroke:#94a3b8; stroke-width:1.3; marker-end:url(#tf-arrow); }
.green-dot { fill:#15803d; }
.amber-dot { fill:#d97706; }
.check { fill:none; stroke:white; stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round; }
.bang { fill:white; font-size:12px; font-weight:700; }
.footer { font-size:10px; letter-spacing:1.2px; fill:#64748b; }
</style>