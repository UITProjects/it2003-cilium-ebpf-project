# Build the three documentation figures. Run from PowerShell on Windows.
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

Begin-Flow '1. Chưa có Tetragon' 'Điều kiện: ứng dụng có lỗ hổng và tiến trình có quyền đọc file nhạy cảm.'
Node "Kẻ tấn công\nkhai thác ứng dụng".Replace('\n',"`n") 35 200
Node "Ứng dụng DVWA\nchạy code của attacker".Replace('\n',"`n") 405 200
Node "Đọc file nhạy cảm\nServiceAccount token".Replace('\n',"`n") 775 200 '#fff2da' '#b47c24'
Node "Thông tin bị lộ\ncó thể bị lạm dụng".Replace('\n',"`n") 1145 200 '#fdebed' '#c04c58'
Edge 320 250 405 250
Edge 690 250 775 250
Edge 1060 250 1145 250 '#c04c58'
Write-Label 'Chưa có Tetragon để ghi nhận process / file access trong luồng thực nghiệm này.' 35 365 22
Write-Label 'Quyền Unix, RBAC và các lớp bảo vệ khác vẫn có thể hạn chế hành vi.' 35 410 20
End-Flow 'flow-without-tetragon.png'

Begin-Flow '2. Command Injection: quan sát tiến trình được thực thi' 'Lệnh chèn vào ứng dụng có thể tạo shell hoặc chương trình con mới.'
Node 'Command Injection' 35 220
Node "Tạo tiến trình mới\nsh / cat / curl".Replace('\n',"`n") 405 220
Node "Tetragon\ngiám sát thực thi".Replace('\n',"`n") 775 220
Node "Monitor\nghi nhận sự kiện".Replace('\n',"`n") 1145 145 '#e8f5eb' '#418752'
Node "Enforce (tùy chọn)\nchặn khi khớp rule".Replace('\n',"`n") 1145 320 '#fdebed' '#c04c58'
Edge 320 270 405 270
Edge 690 270 775 270
Edge 1060 245 1145 195 '#418752'
Edge 1060 295 1145 370 '#c04c58' $true
Write-Label 'Ghi log khác với chặn. Cần rule enforcement phù hợp để ngăn hành vi.' 35 450 22
End-Flow 'flow-command-injection.png'

Begin-Flow '3. File Inclusion: cần theo dõi thao tác đọc file' 'Việc đọc có thể nằm trong web/PHP worker có sẵn, không tạo shell hay process mới.'
Node 'File Inclusion' 35 220
Node "Web / PHP worker\nđang chạy sẵn".Replace('\n',"`n") 405 220
Node "Tetragon: rule đọc file\nsecurity_file_permission".Replace('\n',"`n") 775 220 '#fff2da' '#b47c24'
Node "Monitor\nghi event đọc token".Replace('\n',"`n") 1145 145 '#e8f5eb' '#418752'
Node "Override (tùy chọn)\ntừ chối read: -13".Replace('\n',"`n") 1145 320 '#fdebed' '#c04c58'
Edge 320 270 405 270
Edge 690 270 775 270
Edge 1060 245 1145 195 '#418752'
Edge 1060 295 1145 370 '#c04c58' $true
Write-Label 'Chỉ quan sát tạo tiến trình có thể bỏ sót. Rule file access phải khớp Pod, đường dẫn và thao tác đọc.' 35 450 21
End-Flow 'flow-file-inclusion.png'

