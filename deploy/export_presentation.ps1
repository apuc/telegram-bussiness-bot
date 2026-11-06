# Встраивает шрифт Donbass в PPTX и сохраняет PDF через PowerPoint.
# Запуск из корня проекта после generate_presentation.py:  powershell -File deploy\export_presentation.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pptx = Join-Path $root "ИИ_Пресс-секретарь_презентация.pptx"
$pdf  = Join-Path $root "ИИ_Пресс-секретарь_презентация.pdf"
$tmp  = Join-Path $env:TEMP "press-deck-embedded.pptx"

$app = New-Object -ComObject PowerPoint.Application
try {
    $deck = $app.Presentations.Open($pptx, $false, $false, $false)
    # ppSaveAsOpenXMLPresentation = 24, EmbedTrueTypeFonts = msoTrue (-1): у получателя без Donbass вид не поменяется
    $deck.SaveAs($tmp, 24, -1)
    # ppSaveAsPDF = 32
    $deck.SaveAs($pdf, 32)
    $deck.Close()
} finally {
    $app.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
Move-Item -Force $tmp $pptx
Write-Host "PPTX (со шрифтом) и PDF готовы"
