# eSCL auto scanner for paperless

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

1. **Run with docker-compose:**
   ```bash
   docker-compose up -d
   ```

2. **Test the API:**
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

| Variable | Required | Description | Default |
|----------| ---------|-------------|---------|
| `SCANNER_IP` | required | IP address or hostname of your eSCL scanner | `printer.local` |
| `SCANNER_PROTOCOL` | | `http` or `https` for eSCL endpoint | `https` |
| `SCANNER_VERIFY_TLS` | | Verify TLS certs (`true`/`false`) | `false` |
| `PAPERLESS_URL` |  required | URL of your Paperless-ngx instance | `http://localhost:8000` |
| `PAPERLESS_TOKEN` |  required | API token from Paperless-ngx | (required) |
| `API_PORT` | | Port for the API server | `5050` |
| `API_HOST` | | Host to bind the API server | `0.0.0.0` |
| `SCAN_USER` | | JobSourceInfo: user name sent to scanner | `admin` |
| `SCAN_MACHINE` | | JobSourceInfo: machine name | `printer` |
| `SCAN_APP` | | JobSourceInfo: application name | `EWS-WebScan` |
| `SCAN_COMPRESSION` | | Compression factor in XML | `25` |

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
curl "http://localhost:5050/scan
curl "http://localhost:5050/scan?color_mode=RGB24&resolution=300&title=Invoice"
```


**Parameters:**
- `color_mode`: `RGB24` (default), `Grayscale8`, or `BlackAndWhite1`
- `resolution`: DPI (default: 300)
- `source`: `Platen` or `Feeder` (ADF). If omitted, auto-detects and prefers `Feeder` when available.
- `title`: Document title in Paperless (optional)

### Auto-scan Mode

**GET** `/autoscan/enable`  
Enable automatic scanning when document detected in ADF (Automatic Document Feeder)

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

## Home Assistant Integration (Optional) (for fun)

### 1. Add REST Commands

Edit your Home Assistant `configuration.yaml`:

```yaml
rest_command:
  scan_simple:
    url: "http://YOUR_SERVER_IP:5050/scan"
    method: GET
  
  autoscan_enable:
    url: "http://YOUR_SERVER_IP:5050/autoscan/enable"
    method: GET
  
  autoscan_disable:
    url: "http://YOUR_SERVER_IP:5050/autoscan/disable"
    method: GET

# Binary sensor to track auto-scan status
binary_sensor:
  - platform: rest
    name: "Scanner Auto-scan"
    unique_id: scanner_autoscan_status
    resource: "http://YOUR_SERVER_IP:5050/autoscan/status"
    value_template: "{{ value_json.enabled }}"
    device_class: running
    scan_interval: 10

# Template switch to control auto-scan with on/off toggle
switch:
  - platform: template
    switches:
      scanner_autoscan:
        friendly_name: "Scanner Auto-Scan"
        unique_id: scanner_autoscan_switch
        value_template: "{{ is_state('binary_sensor.scanner_auto_scan', 'on') }}"
        turn_on:
          service: rest_command.autoscan_enable
        turn_off:
          service: rest_command.autoscan_disable
        icon_template: >-
          {% if is_state('binary_sensor.scanner_auto_scan', 'on') %}
            mdi:autorenew
          {% else %}
            mdi:pause
          {% endif %}

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
```

The switch will show the current auto-scan status and allow you to toggle it on/off directly from the UI.

## Docker Deployment

### Build and Run

```bash
# Build the image
docker build -t python-escl-paperless-auto-scanner .

# Run with environment variables
docker run -d \
  --name python-escl-paperless-auto-scanner \
  -p 5050:5050 \
  -e SCANNER_IP=printer.local \
  -e SCANNER_PROTOCOL=https \
  -e SCANNER_VERIFY_TLS=false \
  -e PAPERLESS_URL=http://paperless:8000 \
  -e PAPERLESS_TOKEN=your_token_here \
  python-escl-paperless-auto-scanner
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


## Development

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run in debug mode
export FLASK_ENV=development
python scan_api.py

# Test endpoints
curl http://localhost:5050/health
curl "http://localhost:5050/scan?source=Feeder&resolution=300&color_mode=RGB24"

## Troubleshooting

- 409 Conflict from `/eSCL/ScanJobs`: Ensure the XML matches your device’s expectations. This project defaults to the HP Web UI-compatible payload (Brightness/Contrast/Duplex, JobSourceInfo, CompressionFactor, and `ContentRegionUnits=escl:ThreeHundredthsOfInches`). Also verify `source=Feeder` for ADF.
- TLS errors to `https://<printer>/eSCL`: Set `SCANNER_VERIFY_TLS=false` (equivalent to curl `--insecure`) or provide proper CA certs and set `SCANNER_VERIFY_TLS=true`.
- Paperless upload failures: Confirm `PAPERLESS_TOKEN` and `PAPERLESS_URL` are correct, and that Paperless is reachable from the container.
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
