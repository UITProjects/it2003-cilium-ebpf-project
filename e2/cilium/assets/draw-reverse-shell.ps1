# Build the DVWA reverse-shell documentation figure. Run from PowerShell on Windows.
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = 'Stop'
function Begin-Flow([string]$Title, [string]$Subtitle) {
    $script:canvas = New-Object System.Drawing.Bitmap(1500, 520)
    $script:graphics = [System.Drawing.Graphics]::FromImage($canvas)
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.Clear([System.Drawing.Color]::White)
    Write-Label $Title 35 25 30
    Write-Label $Subtitle 35 78 20
}
function Write-Label([string]$Value,[float]$X,[float]$Y,[float]$Size=20,[string]$Color='#24364b') {
    $font = New-Object System.Drawing.Font('Segoe UI',$Size,[System.Drawing.FontStyle]::Regular,[System.Drawing.GraphicsUnit]::Pixel)
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml($Color))
    $graphics.DrawString($Value,$font,$brush,$X,$Y)
    $brush.Dispose(); $font.Dispose()
}
function Node([string]$Value,[float]$X,[float]$Y,[string]$Fill='#eaf2ff',[string]$Stroke='#5077b0') {
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml($Fill))
    $pen = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml($Stroke),2)
    $rectangle = [System.Drawing.RectangleF]::new($X,$Y,285,100)
    $graphics.FillRectangle($brush,$rectangle)
    $graphics.DrawRectangle($pen,$X,$Y,285,100)
    $font = New-Object System.Drawing.Font('Segoe UI',22,[System.Drawing.FontStyle]::Regular,[System.Drawing.GraphicsUnit]::Pixel)
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $graphics.DrawString($Value,$font,[System.Drawing.Brushes]::Black,$rectangle,$format)
    $format.Dispose(); $font.Dispose(); $pen.Dispose(); $brush.Dispose()
}
function Edge([float]$X1,[float]$Y1,[float]$X2,[float]$Y2,[string]$Color='#5077b0',[bool]$Dashed=$false) {
    $pen = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml($Color),3)
    $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(5,6)
    $pen.CustomEndCap = $cap
    if ($Dashed) { $pen.DashStyle=[System.Drawing.Drawing2D.DashStyle]::Dash }
    $graphics.DrawLine($pen,$X1,$Y1,$X2,$Y2)
    $pen.Dispose(); $cap.Dispose()
}
function End-Flow([string]$Name) {
    $canvas.Save((Join-Path $PSScriptRoot $Name),[System.Drawing.Imaging.ImageFormat]::Png)
    $graphics.Dispose(); $canvas.Dispose()
}

Begin-Flow 'Reverse shell từ DVWA: Cilium chặn kết nối callback' 'Case e2: shell có thể vẫn được tạo; policy kiểm soát đường mạng ra ngoài Pod.'
Node "DVWA\nCommand Injection".Replace('\n',"`n") 35 200
Node "Shell trong Pod\nthử kết nối ra ngoài".Replace('\n',"`n") 405 200
Node "Cilium egress policy\nkiểm soát kết nối".Replace('\n',"`n") 775 200 '#fff2da' '#b47c24'
Node "Máy lab nhận callback\nTCP 4444 / 80 / 443".Replace('\n',"`n") 1145 200 '#fdebed' '#c04c58'
Edge 320 250 405 250
Edge 690 250 775 250
Edge 1060 250 1145 250 '#c04c58' $true
Write-Label 'CHẶN' 1070 205 19 '#c04c58'
Write-Label 'Giữ hoạt động: web ingress TCP 80; DNS qua CoreDNS TCP/UDP 53; ping IPv4 (ICMP type 8).' 35 355 22
Write-Label 'Tetragon: quan sát process; cần rule enforcement riêng nếu muốn dừng process.' 35 405 21
Write-Label 'Chỉ có log hoặc timeout chưa chứng minh chặn: đối chiếu Hubble Policy denied.' 35 450 21
End-Flow 'flow-reverse-shell.png'
