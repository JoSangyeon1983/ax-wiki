param([Parameter(Mandatory=$true)][string]$InputDocx,
      [Parameter(Mandatory=$true)][string]$OutputPdf,
      [string]$PagesJson)
$ErrorActionPreference = 'Stop'
$inputPath = (Resolve-Path -LiteralPath $InputDocx).Path
$outputPath = [IO.Path]::GetFullPath($OutputPdf)
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($outputPath)) | Out-Null
$wordApp = $null
$wordDoc = $null
try {
    $wordApp = New-Object -ComObject Word.Application
    $wordApp.Visible = $false
    $wordApp.DisplayAlerts = -1
    $wordDoc = $wordApp.Documents.Open($inputPath, $false, $true, $false)
    Write-Output 'Opened successfully with Word alerts enabled.'
    $nativeHeadingRanges = @{}
    if ($PagesJson) {
        $wordDoc.Bookmarks.ShowHidden = $true
        foreach ($bookmarkItem in $wordDoc.Bookmarks) {
            if ($bookmarkItem.Name -like '_CaveHeading*') {
                $nativeHeadingRanges[$bookmarkItem.Name] = $bookmarkItem.Range.Duplicate
            }
        }
    }
    $wordDoc.Repaginate()
    foreach ($toc in $wordDoc.TablesOfContents) { $toc.Update() }
    $wordDoc.Fields.Update() | Out-Null
    $wordDoc.Repaginate()
    $wordDoc.ExportAsFixedFormat($outputPath, 17)
    if ($PagesJson) {
        $pageMap = @{}
        foreach ($headingName in $nativeHeadingRanges.Keys) {
            $pageMap[$headingName] = $nativeHeadingRanges[$headingName].Information(1)
        }
        [IO.File]::WriteAllText([IO.Path]::GetFullPath($PagesJson), ($pageMap | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
    }
    Write-Output ('Pages: ' + $wordDoc.ComputeStatistics(2))
    Write-Output ('PDF: ' + $outputPath)
} finally {
    $saveOption = 0
    if ($null -ne $wordDoc) { $wordDoc.Close([ref]$saveOption) }
    if ($null -ne $wordApp) { $wordApp.Quit([ref]$saveOption) }
    if ($null -ne $wordDoc) { [Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordDoc) | Out-Null }
    if ($null -ne $wordApp) { [Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordApp) | Out-Null }
}
