# Rebuild documentation diagrams: powershell -File ./assets/draw-diagrams.ps1
# The architecture figure is redrawn from the image supplied in the conversation.
Add-Type -AssemblyName System.Drawing
$ErrorActionPreference = 'Stop'
function Start-Figure([int]$Width, [int]$Height) {
    $script:bitmap = New-Object System.Drawing.Bitmap($Width, $Height)
    $script:g = [System.Drawing.Graphics]::FromImage($bitmap)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $g.Clear([System.Drawing.Color]::White)
}
function Text([string]$Value, [float]$X, [float]$Y, [float]$Size=20, [string]$Color='#183047') {
    $font = New-Object System.Drawing.Font('Segoe UI', $Size, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml($Color))
    $g.DrawString($Value, $font, $brush, $X, $Y)
    $brush.Dispose(); $font.Dispose()
}
function Box([string]$Value, [float]$X, [float]$Y, [float]$Width=180, [string]$Fill='#e6f4e8', [string]$Stroke='#36844b') {
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml($Fill))
    $pen = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml($Stroke), 2)
    $g.FillRectangle($brush, $X, $Y, $Width, 62)
    $g.DrawRectangle($pen, $X, $Y, $Width, 62)
    $fontSize = 21
    $longestLine = ($Value -split "`n" | Sort-Object Length -Descending | Select-Object -First 1)
    do {
        $font = New-Object System.Drawing.Font('Segoe UI', $fontSize, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
        if ($g.MeasureString($longestLine, $font).Width -le ($Width - 14) -or $fontSize -le 15) { break }
        $font.Dispose(); $fontSize--
    } while ($true)
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    $g.DrawString($Value, $font, [System.Drawing.Brushes]::Black, [System.Drawing.RectangleF]::new($X,$Y,$Width,62), $format)
    $format.Dispose(); $font.Dispose(); $pen.Dispose(); $brush.Dispose()
}
function Arrow([float]$X1,[float]$Y1,[float]$X2,[float]$Y2,[string]$Color='#668078',[bool]$Dashed=$false) {
    $pen = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml($Color), 3)
    $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(5,6)
    $pen.CustomEndCap = $cap
    if ($Dashed) { $pen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash }
    $g.DrawLine($pen,$X1,$Y1,$X2,$Y2)
    $pen.Dispose(); $cap.Dispose()
}
function Curve([float[]]$P,[string]$Color) {
    $pen = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml($Color), 3)
    $cap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(5,6)
    $pen.CustomEndCap = $cap; $pen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash
    $g.DrawBezier($pen,$P[0],$P[1],$P[2],$P[3],$P[4],$P[5],$P[6],$P[7])
    $pen.Dispose(); $cap.Dispose()
}
function Save-Figure([string]$Name) {
    $bitmap.Save((Join-Path $PSScriptRoot $Name), [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bitmap.Dispose()
}

Start-Figure 1480 900
Text 'Online Boutique - application call graph' 40 24 30
Text 'Redrawn from the supplied architecture image. Arrows show connection initiation.' 40 67 19
$nodes = @{
    loadgenerator=@(650,120,180); frontend=@(650,255,180)
    ad=@(65,445,170); recommendation=@(290,445,205)
    productcatalog=@(320,650,210); cart=@(650,650,180)
    shipping=@(895,650,180); currency=@(1130,650,180)
    checkout=@(1130,405,180); payment=@(1290,275,160)
    email=@(1290,525,160); 'Redis cache'=@(650,790,180)
}
$edges = @(
    @('loadgenerator','frontend'),@('frontend','ad'),@('frontend','recommendation'),
    @('frontend','productcatalog'),@('frontend','cart'),@('frontend','shipping'),
    @('frontend','currency'),@('frontend','checkout'),@('recommendation','productcatalog'),
    @('checkout','productcatalog'),@('checkout','cart'),@('checkout','shipping'),
    @('checkout','currency'),@('checkout','payment'),@('checkout','email'),@('cart','Redis cache')
)
foreach ($edge in $edges) {
    $a=$nodes[$edge[0]]; $b=$nodes[$edge[1]]
    $ax=$a[0]+$a[2]/2; $ay=$a[1]+31; $bx=$b[0]+$b[2]/2; $by=$b[1]+31
    $dx=$bx-$ax; $dy=$by-$ay
    $startScale=[Math]::Min([double](($a[2]/2)/[Math]::Max([Math]::Abs($dx),1)),[double](31/[Math]::Max([Math]::Abs($dy),1)))
    $endScale=[Math]::Min([double](($b[2]/2)/[Math]::Max([Math]::Abs($dx),1)),[double](31/[Math]::Max([Math]::Abs($dy),1)))
    Arrow ($ax+$dx*$startScale) ($ay+$dy*$startScale) ($bx-$dx*$endScale) ($by-$dy*$endScale)
}
foreach ($name in $nodes.Keys) {
    $p=$nodes[$name]; $fill='#e6f4e8'; $stroke='#36844b'
    if ($name -in @('frontend','loadgenerator')) { $fill='#e2efff'; $stroke='#4776ad' }
    if ($name -eq 'Redis cache') { $fill='#fff0d6'; $stroke='#b87821' }
    Box $name $p[0] $p[1] $p[2] $fill $stroke
}
Save-Figure 'architecture-reference.png'

Start-Figure 1920 1270
Text 'Cilium controls - full Online Boutique application' 35 20 32
Text '12 app components | 16 internal paths | DNS + blocked lateral movement' 35 65 21
$g.TranslateTransform(0, -130)
$boundary=New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml('#94a3b8'),2)
$boundary.DashStyle=[System.Drawing.Drawing2D.DashStyle]::Dash
$g.DrawRectangle($boundary,30,235,1850,960); $boundary.Dispose()
Text 'microservices-google-demo | default deny INGRESS + EGRESS' 55 250 23
$controlNodes = @{
    loadgenerator=@(900,310,200); frontend=@(900,460,200)
    ad=@(90,640,200); recommendation=@(350,640,245)
    productcatalog=@(380,890,245); cart=@(900,890,200)
    shipping=@(1190,890,210); currency=@(1490,890,210)
    checkout=@(1490,640,240); payment=@(1660,460,200)
    email=@(1660,790,200); 'Redis cache'=@(900,1080,200)
}
$actualNames = @{
    loadgenerator='loadgenerator'; frontend='frontend'; ad='adservice'
    recommendation='recommendationservice'; productcatalog='productcatalogservice'
    cart='cartservice'; shipping='shippingservice'; currency='currencyservice'
    checkout='checkoutservice'; payment='paymentservice'; email='emailservice'; 'Redis cache'='redis-cart'
}
$podPorts = @{frontend=8080; ad=9555; recommendation=8080; productcatalog=3550; cart=7070; shipping=50051; currency=7000; checkout=5050; payment=50051; email=8080; 'Redis cache'=6379}
if ($controlNodes.Count -ne 12 -or $edges.Count -ne 16) { throw 'Unexpected architecture component or edge count' }
# All 16 edges use the SAME call graph as the reference figure above.
foreach ($edge in $edges) {
    $a=$controlNodes[$edge[0]]; $b=$controlNodes[$edge[1]]
    $ax=$a[0]+$a[2]/2; $ay=$a[1]+31; $bx=$b[0]+$b[2]/2; $by=$b[1]+31
    $dx=$bx-$ax; $dy=$by-$ay
    $startScale=[Math]::Min([double](($a[2]/2)/[Math]::Max([Math]::Abs($dx),1)),[double](31/[Math]::Max([Math]::Abs($dy),1)))
    $endScale=[Math]::Min([double](($b[2]/2)/[Math]::Max([Math]::Abs($dx),1)),[double](31/[Math]::Max([Math]::Abs($dy),1)))
    Arrow ($ax+$dx*$startScale) ($ay+$dy*$startScale) ($bx-$dx*$endScale) ($by-$dy*$endScale) '#20834a'
}
# Two explicitly forbidden connection attempts from frontend.
Curve @(1040,460,1100,350,1630,350,1750,460) '#cf3535'
Text 'BLOCK frontend -> paymentservice :50051' 1160 345 21 '#cf3535'
Curve @(900,505,730,600,720,1111,900,1111) '#cf3535'
Text 'BLOCK frontend -> Redis :6379' 330 1030 21 '#cf3535'
foreach ($name in $controlNodes.Keys) {
    $p=$controlNodes[$name]; $fill='#e6f4e8'; $stroke='#36844b'
    if ($name -in @('frontend','loadgenerator')) { $fill='#e2efff'; $stroke='#4776ad' }
    if ($name -eq 'Redis cache') { $fill='#fff0d6'; $stroke='#b87821' }
    $label=$actualNames[$name]
    if ($podPorts.ContainsKey($name)) { $label += "`nPod TCP " + $podPorts[$name] }
    else { $label += "`nHTTP -> frontend Service:80" }
    Box $label $p[0] $p[1] $p[2] $fill $stroke
}
# One shared DNS permission applies to every app Pod, not only frontend.
Text 'ALL app Pods: allow DNS to CoreDNS only (UDP + TCP 53)' 80 1145 21 '#4776ad'
Arrow 360 1178 360 1240 '#4776ad' $true
Box "CoreDNS (kube-system)`nUDP / TCP 53" 180 1240 360 '#e2efff' '#4776ad'
Text 'Green: allowed initiation; source egress AND destination ingress must match.' 650 1230 21
Text 'Red dashed: denied by default; no direct frontend -> Redis / Payment.' 650 1270 21
Text 'Ports inside app boxes are Pod ports. DNS is a shared namespace rule.' 650 1310 21
Text 'Service translation: frontend 80 -> 8080; emailservice 5000 -> 8080.' 650 1350 21
Save-Figure 'cilium-controls.png'
