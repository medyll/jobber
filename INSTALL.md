# Jobber Installation Guide

This guide provides detailed instructions for installing and configuring Jobber on Windows.

## System Requirements

- **Windows 10 or 11** (64-bit)
- **Python 3.11 or higher**
- **PowerShell 5.1 or higher**
- **At least 4GB RAM** (8GB recommended for Ollama)
- **2GB free disk space**

## Installation Methods

### Method 1: Quick Install (Recommended)

The easiest way to install Jobber is using our PowerShell installation script:

```powershell
# 1. Clone the repository
git clone https://github.com/your-repo/jobber.git
cd jobber

# 2. Run the installation script
.\install.ps1

# 3. Activate the virtual environment
.\.venv\Scripts\Activate.ps1
```

The script will:
- Create a Python virtual environment
- Install all Python dependencies
- Set up Playwright with Chromium
- Create a default configuration file
- Verify Ollama installation (optional)

### Method 2: Manual Installation

If you prefer to install manually:

```powershell
# 1. Clone the repository
git clone https://github.com/your-repo/jobber.git
cd jobber

# 2. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Install Playwright
python -m playwright install chromium

# 5. Create configuration (optional)
copy config.yaml.example config.yaml
```

### Method 3: Without Ollama (Keyword-only mode)

If you don't want to use Ollama's semantic matching:

```powershell
.\install.ps1 -NoOllama
```

Jobber will work in keyword fallback mode, which is faster but less accurate.

## Post-Installation Setup

### Ollama Installation (Optional but Recommended)

For best results, install Ollama for semantic matching:

1. Download and install Ollama from [https://ollama.ai](https://ollama.ai)
2. Start the Ollama service:
   ```powershell
   ollama serve
   ```
3. Pull the recommended model:
   ```powershell
   ollama pull mistral
   ```

### Configuration

Edit `config.yaml` to customize Jobber's behavior:

```yaml
ollama:
  enabled: true          # Set to false to disable Ollama
  base_url: http://localhost:11434
  model: mistral         # Model to use
  timeout: 30            # Timeout in seconds

playwright:
  browser: chromium      # Browser to use
  headless: true         # Run in headless mode
  timeout: 60000         # Timeout in milliseconds

mcp_server:
  host: 0.0.0.0          # Bind address
  port: 9000             # Port to listen on
  max_workers: 4         # Maximum concurrent workers
```

### Environment Variables

Jobber respects these environment variables:

- `OLLAMA_BASE_URL`: Override Ollama server URL
- `JOBBER_CONFIG`: Path to custom config file
- `PYTHONUNBUFFERED`: Set to 1 for better logging

## Service Management

Jobber can be run as a Windows service for the MCP server:

### Install the Service

```powershell
# Run as Administrator
.\jobber-service.ps1 install
```

This will:
- Download and install NSSM (Non-Sucking Service Manager)
- Create a Windows service named "JobberMCP"
- Configure automatic startup on system boot
- Set up logging to `logs/jobber-service.log`

### Service Commands

```powershell
# Start the service
.\jobber-service.ps1 start

# Stop the service
.\jobber-service.ps1 stop

# Check status
.\jobber-service.ps1 status

# Uninstall the service
.\jobber-service.ps1 uninstall
```

## Verification

Test your installation:

```powershell
# Test resume parsing
python src\main.py parse tests\sample_resume.pdf

# Test MCP server (if installed as service)
.\jobber-service.ps1 start
# The server should be running on http://localhost:9000
```

## Troubleshooting

### Common Issues

**Python not found**
- Ensure Python 3.11+ is installed and in your PATH
- Reinstall Python and check "Add to PATH" during installation

**Playwright installation fails**
- Try: `python -m playwright install chromium --with-deps`
- Ensure you have Visual C++ build tools installed

**Ollama not detected**
- Verify Ollama is running: `ollama serve`
- Check the URL in config.yaml matches your Ollama server
- Try disabling Ollama: set `ollama.enabled: false` in config.yaml

**Service fails to start**
- Check logs: `logs/jobber-service.log`
- Verify Python virtual environment is activated
- Ensure all dependencies are installed

### Logs

- **Service logs**: `logs/jobber-service.log`
- **Application logs**: Configured in `config.yaml` (default: `jobber.log`)
- **Playwright traces**: `playwright/.trace` directory

## Upgrading

To upgrade to a new version:

```powershell
# 1. Pull the latest changes
git pull origin main

# 2. Update dependencies
.\.venv\Scripts\Activate.ps1
pip install --upgrade -r requirements.txt

# 3. Restart the service (if applicable)
.\jobber-service.ps1 restart
```

## Uninstallation

To completely remove Jobber:

```powershell
# 1. Uninstall the service (if installed)
.\jobber-service.ps1 uninstall

# 2. Remove the directory
rm -r jobber

# 3. Optionally remove Python virtual environment
rm -r .venv
```

## Next Steps

- [Read the full documentation](README.md)
- [Learn about the configuration options](#configuration)
- [Explore the CLI commands](README.md#cli-reference)
- [Set up service management](#service-management)

Need help? Check the [troubleshooting section](#troubleshooting) or open an issue on GitHub.