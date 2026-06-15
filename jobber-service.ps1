<#
.SYNOPSIS
    Manages Jobber as a Windows service using NSSM.

.DESCRIPTION
    This script allows you to install, start, stop, and uninstall Jobber as a Windows service.
    The service runs the MCP server for integration with other components.

.EXAMPLE
    .\jobber-service.ps1 install
    .\jobber-service.ps1 start
    .\jobber-service.ps1 status
    .\jobber-service.ps1 stop
    .\jobber-service.ps1 uninstall
#>

param (
    [string]$Action = "status"
)

$serviceName = "JobberMCP"
$scriptPath = "$PSScriptRoot\src\mcp_server.py"
$pythonPath = "$PSScriptRoot\.venv\Scripts\python.exe"
$logPath = "$PSScriptRoot\logs\jobber-service.log"
$nssmPath = "$env:ProgramFiles\nssm\nssm.exe"

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

function Test-Admin {
    return ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Download-NSSM {
    Write-ColorText "Downloading NSSM..." -Color "Cyan"
    
    $nssmUrl = "https://nssm.cc/download/nssm-2.24.zip"
    $nssmZip = "$env:TEMP\nssm.zip"
    $nssmDir = "$env:TEMP\nssm"
    
    try {
        # Download NSSM
        Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
        
        # Extract
        if (-not (Test-Path $nssmDir)) {
            New-Item -ItemType Directory -Path $nssmDir -Force
        }
        Expand-Archive -Path $nssmZip -DestinationPath $nssmDir -Force
        
        # Install NSSM
        $installerPath = "$nssmDir\win64\nssm.exe"
        if (Test-Path $installerPath) {
            Copy-Item -Path $installerPath -Destination "$env:ProgramFiles\nssm\nssm.exe" -Force -Recurse
            return "$env:ProgramFiles\nssm\nssm.exe"
        } else {
            Write-ColorText "❌ NSSM installer not found in downloaded archive." -Color "Red"
            return $null
        }
    } catch {
        Write-ColorText "❌ Failed to download NSSM: $_" -Color "Red"
        return $null
    }
}

function Ensure-NSSM {
    if (Test-Path $nssmPath) {
        return $nssmPath
    }
    
    Write-ColorText "NSSM not found. Downloading..." -Color "Cyan"
    return Download-NSSM
}

function Install-Service {
    if (-not (Test-Admin)) {
        Write-ColorText "❌ Administrative privileges required to install services." -Color "Red"
        Write-ColorText "Please run this script as Administrator." -Color "Yellow"
        exit 1
    }
    
    $nssmPath = Ensure-NSSM
    if (-not $nssmPath) {
        exit 1
    }
    
    Write-ColorText "Installing Jobber MCP service..." -Color "Cyan"
    
    # Check if service already exists
    try {
        $service = Get-Service -Name $serviceName -ErrorAction Stop
        Write-ColorText "⚠️  Service already exists. Reinstalling..." -Color "Yellow"
        & $nssmPath remove $serviceName confirm
    } catch {
        # Service doesn't exist, proceed with installation
    }
    
    # Install the service
    & $nssmPath install $serviceName $pythonPath $scriptPath
    if ($LASTEXITCODE -ne 0) {
        Write-ColorText "❌ Failed to install service." -Color "Red"
        exit 1
    }
    
    # Configure service parameters
    & $nssmPath set $serviceName AppDirectory $PSScriptRoot
    & $nssmPath set $serviceName AppStdout $logPath
    & $nssmPath set $serviceName AppStderr $logPath
    & $nssmPath set $serviceName AppEnvironmentExtra "PYTHONUNBUFFERED=1"
    & $nssmPath set $serviceName Start SERVICE_AUTO_START
    & $nssmPath set $serviceName DisplayName "Jobber MCP Server"
    & $nssmPath set $serviceName Description "Jobber MCP Server for job processing and matching"
    
    Write-ColorText "✅ Jobber service installed successfully!" -Color "Green"
    Write-ColorText "Service will start automatically on system boot." -Color "Cyan"
}

function Start-Service {
    if (-not (Test-Admin)) {
        Write-ColorText "❌ Administrative privileges required to start services." -Color "Red"
        exit 1
    }
    
    Write-ColorText "Starting Jobber service..." -Color "Cyan"
    
    try {
        Start-Service -Name $serviceName
        Write-ColorText "✅ Jobber service started!" -Color "Green"
        Write-ColorText "Log file: $logPath" -Color "Cyan"
    } catch {
        Write-ColorText "❌ Failed to start service: $_" -Color "Red"
        exit 1
    }
}

function Stop-Service {
    if (-not (Test-Admin)) {
        Write-ColorText "❌ Administrative privileges required to stop services." -Color "Red"
        exit 1
    }
    
    Write-ColorText "Stopping Jobber service..." -Color "Cyan"
    
    try {
        Stop-Service -Name $serviceName -Force
        Write-ColorText "✅ Jobber service stopped!" -Color "Green"
    } catch {
        Write-ColorText "❌ Failed to stop service: $_" -Color "Red"
        exit 1
    }
}

function Uninstall-Service {
    if (-not (Test-Admin)) {
        Write-ColorText "❌ Administrative privileges required to uninstall services." -Color "Red"
        exit 1
    }
    
    Write-ColorText "Uninstalling Jobber service..." -Color "Cyan"
    
    $nssmPath = Ensure-NSSM
    if (-not $nssmPath) {
        exit 1
    }
    
    try {
        & $nssmPath remove $serviceName confirm
        & $nssmPath reset $serviceName
        Write-ColorText "✅ Jobber service uninstalled!" -Color "Green"
    } catch {
        Write-ColorText "❌ Failed to uninstall service: $_" -Color "Red"
        exit 1
    }
}

function Get-ServiceStatus {
    try {
        $service = Get-Service -Name $serviceName -ErrorAction Stop
        
        Write-ColorText "Jobber service status: $($service.Status)" -Color "Green"
        
        if ($service.Status -eq "Running") {
            Write-ColorText "Service is running (PID: $($service.Id))" -Color "Cyan"
            Write-ColorText "Log file: $logPath" -Color "Cyan"
            
            if (Test-Path $logPath) {
                Write-ColorText "Last 10 log lines:" -Color "Cyan"
                Get-Content $logPath -Tail 10 -ErrorAction SilentlyContinue | ForEach-Object { 
                    Write-ColorText "  $_" -Color "White"
                }
            } else {
                Write-ColorText "Log file not found: $logPath" -Color "Yellow"
            }
        } elseif ($service.Status -eq "Stopped") {
            Write-ColorText "Service is stopped" -Color "Yellow"
        } else {
            Write-ColorText "Service status: $($service.Status)" -Color "Yellow"
        }
    } catch {
        Write-ColorText "Jobber service is not installed" -Color "Yellow"
        Write-ColorText "To install: .\jobber-service.ps1 install" -Color "Cyan"
    }
}

function Show-Help {
    Write-ColorText "Jobber Service Manager" -Color "Magenta"
    Write-ColorText "" -Color "White"
    Write-ColorText "Usage: .\jobber-service.ps1 [action]" -Color "Cyan"
    Write-ColorText "" -Color "White"
    Write-ColorText "Actions:" -Color "Cyan"
    Write-ColorText "  install    - Install Jobber as a Windows service" -Color "Blue"
    Write-ColorText "  start      - Start the Jobber service" -Color "Blue"
    Write-ColorText "  stop       - Stop the Jobber service" -Color "Blue"
    Write-ColorText "  status     - Show service status (default)" -Color "Blue"
    Write-ColorText "  uninstall  - Uninstall the Jobber service" -Color "Blue"
    Write-ColorText "  help       - Show this help message" -Color "Blue"
    Write-ColorText "" -Color "White"
    Write-ColorText "Note: Service actions require administrative privileges" -Color "Yellow"
}

# Main switch
switch ($Action) {
    "install" { Install-Service }
    "start" { Start-Service }
    "stop" { Stop-Service }
    "uninstall" { Uninstall-Service }
    "status" { Get-ServiceStatus }
    "help" { Show-Help }
    default { 
        if ($Action -ne "") {
            Write-ColorText "❌ Unknown action: $Action" -Color "Red"
        }
        Show-Help
    }
}
