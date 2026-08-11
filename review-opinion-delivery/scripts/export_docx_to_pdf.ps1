param(
    [Parameter(Mandatory=$true)][string]$DocxPath,
    [Parameter(Mandatory=$true)][string]$PdfPath
)

$word = $null
$doc = $null
try {
    $docxFull = [System.IO.Path]::GetFullPath($DocxPath)
    $pdfFull = [System.IO.Path]::GetFullPath($PdfPath)
    if (-not (Test-Path -LiteralPath $docxFull)) { throw "DOCX not found: $docxFull" }
    $pdfDir = [System.IO.Path]::GetDirectoryName($pdfFull)
    if (-not (Test-Path -LiteralPath $pdfDir)) { New-Item -ItemType Directory -Path $pdfDir | Out-Null }

    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($docxFull, $false, $true)
    $doc.ExportAsFixedFormat($pdfFull, 17)
}
finally {
    if ($doc -ne $null) { $doc.Close($false) }
    if ($word -ne $null) { $word.Quit() }
    if ($doc -ne $null) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc) }
    if ($word -ne $null) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
