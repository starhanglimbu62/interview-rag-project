
# ==========================================
# Document RAG Backend API Test Suite
# Compatible with Windows PowerShell 5.1
# ==========================================

$BaseUrl = "http://127.0.0.1:8000"
$UploadUrl = "$BaseUrl/api/v1/documents/upload"

$Passed = 0
$Failed = 0

$TempDir = Join-Path $env:TEMP "rag-api-tests"

New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

# ==========================================
# Helper: Record test result
# ==========================================

function Test-Result {
    param(
        [string]$Name,
        [int]$Expected,
        [int]$Actual
    )

    if ($Expected -eq $Actual) {
        Write-Host "[PASS] $Name" -ForegroundColor Green
        $script:Passed++
    }
    else {
        Write-Host "[FAIL] $Name | Expected: $Expected | Actual: $Actual" -ForegroundColor Red
        $script:Failed++
    }
}

# ==========================================
# Helper: Upload file using curl.exe
# ==========================================

function Test-Upload {
    param(
        [string]$Name,
        [string]$Filename,
        [byte[]]$Content,
        [string]$ContentType,
        [int]$Expected
    )

    $FilePath = Join-Path $TempDir $Filename
    $ResponsePath = Join-Path $TempDir "response.json"

    [System.IO.File]::WriteAllBytes($FilePath, $Content)

    try {
        $CurlOutput = & curl.exe `
            --silent `
            --show-error `
            --output $ResponsePath `
            --write-out "%{http_code}" `
            --form "file=@$FilePath;type=$ContentType" `
            $UploadUrl

        if ($LASTEXITCODE -ne 0) {
            throw "curl.exe failed with exit code $LASTEXITCODE"
        }

        $StatusCode = [int](($CurlOutput -join "").Trim())

        $ResponseBody = ""

        if (Test-Path $ResponsePath) {
            $ResponseBody = Get-Content $ResponsePath -Raw
        }

        Test-Result `
            -Name $Name `
            -Expected $Expected `
            -Actual $StatusCode

        return $ResponseBody
    }
    catch {
        Write-Host "[ERROR] $Name : $($_.Exception.Message)" -ForegroundColor Red
        $script:Failed++
        return $null
    }
    finally {
        Remove-Item $FilePath -Force -ErrorAction SilentlyContinue
        Remove-Item $ResponsePath -Force -ErrorAction SilentlyContinue
    }
}

# ==========================================
# 1. Health endpoint
# ==========================================

Write-Host "`n===== HEALTH CHECK =====" -ForegroundColor Cyan

try {
    $Health = Invoke-RestMethod `
        -Uri "$BaseUrl/health" `
        -Method Get `
        -ErrorAction Stop

    if ($Health.status -eq "healthy") {
        Test-Result "Health endpoint" 200 200
    }
    else {
        Test-Result "Health endpoint" 200 500
    }
}
catch {
    Write-Host "[FAIL] Cannot connect to API: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# ==========================================
# 2. Valid TXT upload
# ==========================================

Write-Host "`n===== DOCUMENT UPLOAD TESTS =====" -ForegroundColor Cyan

$ValidTxt = [System.Text.Encoding]::UTF8.GetBytes(
    "FastAPI is a Python framework. This is a test document."
)

Test-Upload `
    -Name "Valid TXT upload" `
    -Filename "sample.txt" `
    -Content $ValidTxt `
    -ContentType "text/plain" `
    -Expected 200 | Out-Null

# ==========================================
# 3. Unsupported file
# ==========================================

Test-Upload `
    -Name "Reject DOCX file" `
    -Filename "sample.docx" `
    -Content ([System.Text.Encoding]::UTF8.GetBytes("test")) `
    -ContentType "application/octet-stream" `
    -Expected 400 | Out-Null

# ==========================================
# 4. Empty file
# ==========================================

Test-Upload `
    -Name "Reject empty file" `
    -Filename "empty.txt" `
    -Content ([byte[]]@()) `
    -ContentType "text/plain" `
    -Expected 400 | Out-Null

# ==========================================
# 5. Invalid PDF
# ==========================================

Test-Upload `
    -Name "Reject invalid PDF" `
    -Filename "fake.pdf" `
    -Content ([System.Text.Encoding]::UTF8.GetBytes("Not a PDF")) `
    -ContentType "application/pdf" `
    -Expected 400 | Out-Null

# ==========================================
# 6. Invalid TXT encoding
# ==========================================

Test-Upload `
    -Name "Reject invalid TXT encoding" `
    -Filename "invalid.txt" `
    -Content ([byte[]]@(255, 254, 250)) `
    -ContentType "text/plain" `
    -Expected 400 | Out-Null

# ==========================================
# 7. Oversized file
# ==========================================

$LargeContent = New-Object byte[] (10 * 1024 * 1024 + 1)

Test-Upload `
    -Name "Reject file larger than 10 MB" `
    -Filename "large.txt" `
    -Content $LargeContent `
    -ContentType "text/plain" `
    -Expected 413 | Out-Null

# ==========================================
# 8. Generate and upload valid PDF
# ==========================================

Write-Host "`n===== PDF EXTRACTION TESTS =====" -ForegroundColor Cyan

$PdfPath = Join-Path $TempDir "valid-sample.pdf"

$PythonCode = @"
import pymupdf

doc = pymupdf.open()
page = doc.new_page()
page.insert_text((72, 72), "This is a valid PDF document.")
doc.save(r"$PdfPath")
doc.close()
"@

$PythonCode | python -

if ($LASTEXITCODE -eq 0 -and (Test-Path $PdfPath)) {

    $PdfBytes = [System.IO.File]::ReadAllBytes($PdfPath)

    $PdfResponse = Test-Upload `
        -Name "Valid PDF upload" `
        -Filename "valid.pdf" `
        -Content $PdfBytes `
        -ContentType "application/pdf" `
        -Expected 200

    if ($PdfResponse) {
        try {
            $PdfJson = $PdfResponse | ConvertFrom-Json

            if ($PdfJson.document.page_count -eq 1) {
                Test-Result "PDF page count" 1 1
            }
            else {
                Test-Result "PDF page count" 1 0
            }
        }
        catch {
            Write-Host "[FAIL] Invalid PDF response JSON" -ForegroundColor Red
            $Failed++
        }
    }

    Remove-Item $PdfPath -Force -ErrorAction SilentlyContinue
}
else {
    Write-Host "[FAIL] Could not generate PDF. Check PyMuPDF installation." -ForegroundColor Red
    $Failed++
}

# ==========================================
# 9. Final report
# ==========================================

Write-Host "`n========== TEST SUMMARY ==========" -ForegroundColor Cyan

Write-Host "Passed: $Passed" -ForegroundColor Green
Write-Host "Failed: $Failed" -ForegroundColor Red

if ($Failed -eq 0) {
    Write-Host "`nALL TESTS PASSED" -ForegroundColor Green
}
else {
    Write-Host "`nTESTS FAILED. DO NOT COMMIT." -ForegroundColor Red
}

# Cleanup
Remove-Item $TempDir -Recurse -Force -ErrorAction SilentlyContinue
