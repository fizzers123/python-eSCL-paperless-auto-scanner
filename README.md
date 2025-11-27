# eSCL Scanner API for Home Assistant

A lightweight REST API that enables scanning from eSCL-compatible printers (HP, Brother, Canon, etc.) to Paperless-ngx, with Home Assistant integration and automatic scanning capabilities.

## Features

✨ **Simple REST API** - Trigger scans via HTTP GET/POST requests  
📄 **Paperless-ngx Integration** - Automatically uploads scanned documents  
🔄 **Auto-scan Mode** - Detects documents in ADF and scans automatically  
🏠 **Home Assistant Ready** - Pre-configured scripts and sensors  
🐳 **Docker Support** - Run in containers with docker-compose  
⚡ **Multiple Color Modes** - RGB, Grayscale, and Black & White  
🎯 **ADF Auto-detection** - Uses document feeder when available

## Quick Start

### Using Docker (Recommended)

1. **Clone and configure:**
   ```bash
   git clone <your-repo-url>
   cd escl-scanner-api
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Run with docker-compose:**
   ```bash
   docker-compose up -d
   ```

3. **Test the API:**
   ```bash
   curl http://localhost:5050/scan
   ```

### Using Python

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Run the API:**
   ```bash
   export $(cat .env | xargs)
   python scan_api.py
   ```

## Configuration

Set these environment variables in `.env` or docker-compose.yml:

| Variable | Description | Default |
|----------|-------------|---------|
| `SCANNER_IP` | IP address or hostname of your eSCL scanner | `printer.local` |
| `PAPERLESS_URL` | URL of your Paperless-ngx instance | `http://localhost:8000` |
| `PAPERLESS_TOKEN` | API token from Paperless-ngx | (required) |
| `API_PORT` | Port for the API server | `5050` |
| `API_HOST` | Host to bind the API server | `0.0.0.0` |

### Getting Paperless API Token

1. Log in to Paperless-ngx
2. Go to Settings → API Tokens
3. Create a new token and copy it

## API Endpoints

### Scan Document

**GET/POST** `/scan`

Trigger a scan with optional parameters.

**GET Example:**
```bash
curl "http://localhost:5050/scan?color_mode=RGB24&resolution=300&title=Invoice"
```

**POST Example:**
```bash
curl -X POST http://localhost:5050/scan \
  -H "Content-Type: application/json" \
  -d '{"color_mode": "Grayscale8", "resolution": 600, "title": "Document"}'
```

**Parameters:**
- `color_mode`: `RGB24` (default), `Grayscale8`, or `BlackAndWhite1`
- `resolution`: DPI (default: 300)
- `source`: `Platen`, `Adf`, or auto-detect if not specified
- `title`: Document title in Paperless (optional)

### Auto-scan Mode

**GET** `/autoscan/enable`  
Enable automatic scanning when document detected in ADF

**GET** `/autoscan/disable`  
Disable automatic scanning

**GET** `/autoscan/status`  
Check if auto-scan is enabled

**Examples:**
```bash
curl http://localhost:5050/autoscan/enable
curl http://localhost:5050/autoscan/status
```

### Health Check

**GET** `/health`

Check if the API is running.

```bash
curl http://localhost:5050/health
```

## Home Assistant Integration

### 1. Add REST Commands

Edit your Home Assistant `configuration.yaml`:

```yaml
rest_command:
  scan_simple:
    url: "http://YOUR_SERVER_IP:5050/scan"
    method: GET
  
  scan_color:
    url: "http://YOUR_SERVER_IP:5050/scan"
    method: POST
    content_type: "application/json"
    payload: '{"color_mode": "RGB24", "resolution": 300}'
  
  autoscan_enable:
    url: "http://YOUR_SERVER_IP:5050/autoscan/enable"
    method: GET
  
  autoscan_disable:
    url: "http://YOUR_SERVER_IP:5050/autoscan/disable"
    method: GET

sensor:
  - platform: rest
    name: "Scanner Auto-scan Status"
    resource: "http://YOUR_SERVER_IP:5050/autoscan/status"
    value_template: "{{ value_json.enabled }}"
    scan_interval: 30

script:
  scan_now:
    alias: "Scan Now"
    icon: mdi:scanner
    sequence:
      - service: rest_command.scan_simple
      - service: notify.notify
        data:
          title: "Scanner"
          message: "Scan started"
  
  autoscan_enable:
    alias: "Enable Auto-Scan"
    icon: mdi:autorenew
    sequence:
      - service: rest_command.autoscan_enable
```

### 2. Add Dashboard Card

```yaml
type: vertical-stack
cards:
  - type: horizontal-stack
    cards:
      - type: button
        name: Scan Now
        icon: mdi:scanner
        tap_action:
          action: call-service
          service: script.scan_now
      - type: button
        name: Auto-Scan
        icon: mdi:autorenew
        tap_action:
          action: call-service
          service: script.autoscan_enable
  - type: entity
    entity: sensor.scanner_auto_scan_status
    name: Auto-Scan Status
```

## Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t escl-scanner-api .

# Run with environment variables
docker run -d \
  --name escl-scanner-api \
  -p 5050:5050 \
  -e SCANNER_IP=printer.local \
  -e PAPERLESS_URL=http://paperless:8000 \
  -e PAPERLESS_TOKEN=your_token_here \
  escl-scanner-api
```

### Using docker-compose

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Systemd Service (Alternative)

If not using Docker, run as a systemd service:

1. **Create service file** `/etc/systemd/system/escl-scanner-api.service`:

```ini
[Unit]
Description=eSCL Scanner API
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/escl-scanner-api
Environment="SCANNER_IP=printer.local"
Environment="PAPERLESS_URL=http://localhost:8000"
Environment="PAPERLESS_TOKEN=your_token"
ExecStart=/usr/bin/python3 /path/to/escl-scanner-api/scan_api.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. **Enable and start:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable escl-scanner-api
sudo systemctl start escl-scanner-api
sudo systemctl status escl-scanner-api
```

## Compatible Printers

This API works with any printer supporting the eSCL (AirPrint) protocol:

- HP (most modern models)
- Brother
- Canon
- Epson
- Xerox
- And many others with AirPrint support

## Troubleshooting

### Can't connect to scanner

```bash
# Test scanner connectivity
curl http://SCANNER_IP/eSCL/ScannerCapabilities

# Check if scanner supports eSCL
nmap -p 80,443,8080,8443 SCANNER_IP
```

### Auto-scan not working

1. Check scanner status: `curl http://localhost:5050/autoscan/status`
2. Verify ADF support: Check scanner capabilities
3. Review logs: `docker-compose logs -f` or `journalctl -u escl-scanner-api -f`

### Paperless upload fails

1. Verify Paperless URL is accessible from the API
2. Check API token is valid
3. Ensure Paperless accepts the token (test with curl)

## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run in debug mode
export FLASK_ENV=development
python scan_api.py

# Test endpoints
curl http://localhost:5050/health
curl http://localhost:5050/scan
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details

## Acknowledgments

- Built for [Home Assistant](https://www.home-assistant.io/)
- Integrates with [Paperless-ngx](https://github.com/paperless-ngx/paperless-ngx)
- Uses eSCL protocol (Apple AirPrint scanning)

## Support

- Report issues on GitHub
- Check existing issues before creating new ones
- Provide logs and configuration details when reporting problems
