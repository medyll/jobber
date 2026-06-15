<#
Test Jobber Installation

This script verifies that Jobber is properly installed and configured.
#>

Write-Host "🔍 Testing Jobber Installation..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Check Python installation
Write-Host "1. Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "   ✅ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Python not found" -ForegroundColor Red
    exit 1
}

# Test 2: Check virtual environment
Write-Host "2. Checking virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "   ✅ Virtual environment exists" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Virtual environment not found (run install.ps1)" -ForegroundColor Yellow
}

# Test 3: Check configuration file
Write-Host "3. Checking configuration..." -ForegroundColor Yellow
if (Test-Path "config.yaml") {
    Write-Host "   ✅ Configuration file found" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  Configuration file not found (run install.ps1)" -ForegroundColor Yellow
}

# Test 4: Check required directories
Write-Host "4. Checking directories..." -ForegroundColor Yellow
$requiredDirs = @("data", "temp", "cache/resumes", "logs")
$allDirsExist = $true
foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir)) {
        Write-Host "   ⚠️  Directory missing: $dir" -ForegroundColor Yellow
        $allDirsExist = $false
    }
}
if ($allDirsExist) {
    Write-Host "   ✅ All required directories exist" -ForegroundColor Green
}

# Test 5: Check Python dependencies
Write-Host "5. Checking Python dependencies..." -ForegroundColor Yellow
try {
    $dependencies = @("PyPDF2", "pdfminer.six", "python-docx", "beautifulsoup4", "requests", "sentence-transformers", "mcp")
    $missingDeps = @()
    
    foreach ($dep in $dependencies) {
        $result = python -c "import $dep" 2>&1
        if ($LASTEXITCODE -ne 0) {
            $missingDeps += $dep
        }
    }
    
    if ($missingDeps.Count -eq 0) {
        Write-Host "   ✅ All Python dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Missing dependencies: $($missingDeps -join ', ')" -ForegroundColor Yellow
        Write-Host "   Run: pip install -r requirements.txt" -ForegroundColor Cyan
    }
} catch {
    Write-Host "   ❌ Failed to check dependencies: $_" -ForegroundColor Red
}

# Test 6: Check Playwright
Write-Host "6. Checking Playwright..." -ForegroundColor Yellow
try {
    $playwrightVersion = python -m playwright --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Playwright installed: $playwrightVersion" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Playwright not found (run: python -m playwright install chromium)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "   ❌ Playwright check failed: $_" -ForegroundColor Red
}

# Test 7: Check Ollama (optional)
Write-Host "7. Checking Ollama (optional)..." -ForegroundColor Yellow
try {
    $ollamaVersion = ollama --version 2>&1
    Write-Host "   ✅ Ollama found: $ollamaVersion" -ForegroundColor Green
} catch {
    Write-Host "   ⚠️  Ollama not found (optional)" -ForegroundColor Yellow
    Write-Host "   Install from: https://ollama.ai" -ForegroundColor Cyan
}

# Test 8: Test configuration loading
Write-Host "8. Testing configuration loading..." -ForegroundColor Yellow
try {
    $configTest = python -c "import sys; sys.path.insert(0, 'src'); from config import get_config; config = get_config(); print('OK')" 2>&1
    if ($configTest -match "OK") {
        Write-Host "   ✅ Configuration module works" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Configuration loading failed" -ForegroundColor Red
    }
} catch {
    Write-Host "   ❌ Configuration test failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "📊 Installation Summary:" -ForegroundColor Magenta
Write-Host ""

$summary = @()

# Count issues
$warnings = 0
$errors = 0

if (-not (Test-Path ".venv\Scripts\python.exe")) { $warnings++ }
if (-not (Test-Path "config.yaml")) { $warnings++ }
if (-not $allDirsExist) { $warnings++ }

if ($missingDeps.Count -gt 0) { $warnings++ }

if ($warnings -eq 0) {
    Write-Host "✅ All checks passed! Jobber is ready to use." -ForegroundColor Green
    $summary += "Status: Ready"
} else {
    Write-Host "⚠️  Installation has $warnings warning(s)." -ForegroundColor Yellow
    $summary += "Status: Needs attention"
}

$summary += "Python: $pythonVersion"
$summary += "Virtual Environment: $(if (Test-Path '.venv') { 'Present' } else { 'Missing' })"
$summary += "Configuration: $(if (Test-Path 'config.yaml') { 'Present' } else { 'Missing' })"
$summary += "Dependencies: $(if ($missingDeps.Count -eq 0) { 'Complete' } else { 'Incomplete' })"

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
if ($warnings -gt 0) {
    Write-Host "  • Run .\install.ps1 to fix missing components" -ForegroundColor Blue
}
Write-Host "  • Activate virtual environment: .\.venv\Scripts\Activate.ps1" -ForegroundColor Blue
Write-Host "  • Test Jobber: python src\main.py parse your_resume.pdf" -ForegroundColor Blue
Write-Host "  • Start MCP server: python src\mcp_server.py" -ForegroundColor Blue
Write-Host "  • Install as service: .\jobber-service.ps1 install (Admin)" -ForegroundColor Blue
Write-Host ""

Write-Host "Details:" -ForegroundColor Cyan
foreach ($item in $summary) {
    Write-Host "  $item" -ForegroundColor White
}
