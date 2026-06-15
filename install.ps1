# install.ps1
<#
.SYNOPSIS
    Installs Jobber and all its dependencies automatically.

.DESCRIPTION
    This script sets up Jobber with all required dependencies:
    - Creates a Python virtual environment
    - Installs Python packages from requirements.txt
    - Sets up Playwright with Chromium
    - Configures environment variables
    - Verifies Ollama installation (optional)

.EXAMPLE
    .\install.ps1
    .\install.ps1 -NoOllama
#>

param (
    [switch]$NoOllama
)

# Check if running as administrator for service installation
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

function Write-ColorText {
    param (
        [string]$Text,
        [string]$Color = "White"
    )
    
    $colors = @{
        "Red" = "[91m"
        "Green" = "[92m"
        "Yellow" = "[93m"
        "Blue" = "[94m"
        "Magenta" = "[95m"
        "Cyan" = "[96m"
        "White" = "[97m"
    }
    
    if ($colors.ContainsKey($Color)) {
        Write-Host "`e$($colors[$Color])$Text`e[0m"
    } else {
        Write-Host $Text
    }
}

# Check Python 3.11+ is installed
Write-ColorText "Checking Python installation..." -Color "Cyan"
$pythonPath = where python 2>$null
if (-not $pythonPath) {
    Write-ColorText "❌ Python 3.11+ is required but not found." -Color "Red"
    Write-ColorText "Please install Python from https://www.python.org/downloads/" -Color "Yellow"
    exit 1
}

$pythonVersion = python --version 2>&1
Write-ColorText "Found Python: $pythonVersion" -Color "Green"

if (-not ($pythonVersion -match "Python 3\.1[1-9]|Python 3\.[2-9]")) {
    Write-ColorText "⚠️  Python 3.11+ is recommended. You have: $pythonVersion" -Color "Yellow"
}

# Create virtual environment
Write-ColorText "Creating Python virtual environment..." -Color "Cyan"
if (Test-Path ".venv") {
    Write-ColorText "⚠️  Virtual environment already exists. Skipping creation." -Color "Yellow"
} else {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-ColorText "❌ Failed to create virtual environment." -Color "Red"
        exit 1
    }
}

# Activate virtual environment
Write-ColorText "Activating virtual environment..." -Color "Cyan"
if (Test-Path ".venv\Scripts\Activate.ps1") {
    . .venv\Scripts\Activate.ps1
} else {
    Write-ColorText "❌ Virtual environment activation failed." -Color "Red"
    exit 1
}

# Install Python dependencies
Write-ColorText "Installing Python dependencies..." -Color "Cyan"
pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-ColorText "❌ Failed to upgrade pip." -Color "Red"
    exit 1
}

pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-ColorText "❌ Failed to install requirements." -Color "Red"
    exit 1
}

# Install Playwright with Chromium
Write-ColorText "Setting up Playwright with Chromium..." -Color "Cyan"
python -m playwright install chromium
if ($LASTEXITCODE -ne 0) {
    Write-ColorText "❌ Failed to install Playwright." -Color "Red"
    exit 1
}

# Check Ollama (unless --NoOllama specified)
if (-not $NoOllama) {
    Write-ColorText "Checking Ollama installation..." -Color "Cyan"
    try {
        $ollamaVersion = ollama --version 2>&1
        Write-ColorText "✅ Ollama found: $ollamaVersion" -Color "Green"
    } catch {
        Write-ColorText "⚠️  Ollama not found." -Color "Yellow"
        Write-ColorText "   Jobber will work in keyword fallback mode, but semantic matching will be disabled." -Color "Yellow"
        Write-ColorText "   To install Ollama: https://ollama.ai" -Color "Blue"
    }
} else {
    Write-ColorText "⚠️  Skipping Ollama check (--NoOllama specified)" -Color "Yellow"
}

# Create default config file
Write-ColorText "Creating default configuration..." -Color "Cyan"
$configContent = @"
# Jobber Configuration
# This file controls Jobber's behavior and integration with other services

ollama:
  enabled: true
  base_url: http://localhost:11434
  model: mistral
  timeout: 30

playwright:
  browser: chromium
  headless: true
  timeout: 60000

logging:
  level: INFO
  file: jobber.log
  max_size: 10MB
  backup_count: 5
  format: "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s"

paths:
  data_dir: data
  temp_dir: temp
  resume_cache: cache/resumes

mcp_server:
  host: 0.0.0.0
  port: 9000
  max_workers: 4
"@

$configContent | Out-File -FilePath config.yaml -Encoding utf8 -Force

# Create necessary directories
Write-ColorText "Creating necessary directories..." -Color "Cyan"
$directories = @("data", "temp", "cache/resumes", "logs")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
        Write-ColorText "   Created directory: $dir" -Color "Green"
    }
}

Write-ColorText "" -Color "White"
Write-ColorText "✅ Jobber installation complete!" -Color "Green"
Write-ColorText "" -Color "White"
Write-ColorText "Next steps:" -Color "Cyan"
Write-ColorText "1. Activate the virtual environment: .\.venv\Scripts\Activate.ps1" -Color "Blue"
Write-ColorText "2. Start Ollama if you want semantic matching: ollama serve" -Color "Blue"
Write-ColorText "3. Run Jobber: python src\main.py parse your_resume.pdf" -Color "Blue"
Write-ColorText "4. Or start the MCP server: python src\mcp_server.py" -Color "Blue"
Write-ColorText "" -Color "White"
Write-ColorText "For service installation (requires admin):" -Color "Cyan"
Write-ColorText "   .\jobber-service.ps1 install" -Color "Blue"
Write-ColorText "   .\jobber-service.ps1 start" -Color "Blue"
Write-ColorText "" -Color "White"
Write-ColorText "Documentation: See INSTALL.md and README.md" -Color "Cyan"
