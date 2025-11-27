#!/usr/bin/env python3
"""
eSCL Scanner API for Home Assistant
Scans documents from HP printers using eSCL protocol and uploads to Paperless-ngx
"""

from flask import Flask, request, jsonify
import requests
import time
import os
from datetime import datetime

app = Flask(__name__)

# Configuration from environment variables
SCANNER_IP = os.getenv("SCANNER_IP", "printer.local")
PAPERLESS_URL = os.getenv("PAPERLESS_URL", "http://localhost:8000")
PAPERLESS_TOKEN = os.getenv("PAPERLESS_TOKEN", "")
API_PORT = int(os.getenv("API_PORT", "5050"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# Auto-scan mode state
AUTO_SCAN_ENABLED = False


class ESCLScanner:
    """Handle eSCL scanning operations"""

    def __init__(self, scanner_ip):
        self.scanner_ip = scanner_ip
        self.base_url = f"http://{scanner_ip}/eSCL"

    def get_scanner_status(self):
        """Get scanner status"""
        try:
            response = requests.get(f"{self.base_url}/ScannerStatus", timeout=10)
            response.raise_for_status()
            return response.text
        except:
            return None

    def get_scanner_capabilities(self):
        """Get scanner capabilities and check for ADF"""
        try:
            response = requests.get(f"{self.base_url}/ScannerCapabilities", timeout=10)
            response.raise_for_status()

            # Check if ADF is mentioned in capabilities
            capabilities_text = response.text
            has_adf = "Adf" in capabilities_text or "ADF" in capabilities_text

            return has_adf
        except:
            return False

    def check_adf_loaded(self):
        """Check if document is loaded in ADF"""
        try:
            status = self.get_scanner_status()
            if status:
                # Check for ADF loaded indicators
                return "AdfLoaded" in status or "MediaLoaded" in status
            return False
        except:
            return False

    def create_scan_job(self, settings):
        """Create a scan job with specified settings"""
        scan_settings_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<scan:ScanSettings xmlns:scan="http://schemas.hp.com/imaging/escl/2011/05/03" 
                   xmlns:pwg="http://www.pwg.org/schemas/2010/12/sm">
    <pwg:Version>2.0</pwg:Version>
    <scan:Intent>{settings.get('intent', 'Document')}</scan:Intent>
    <pwg:ScanRegions>
        <pwg:ScanRegion>
            <pwg:XOffset>0</pwg:XOffset>
            <pwg:YOffset>0</pwg:YOffset>
            <pwg:Width>{settings.get('width', 2550)}</pwg:Width>
            <pwg:Height>{settings.get('height', 3300)}</pwg:Height>
        </pwg:ScanRegion>
    </pwg:ScanRegions>
    <pwg:InputSource>{settings.get('input_source', 'Platen')}</pwg:InputSource>
    <scan:DocumentFormatExt>{settings.get('format', 'application/pdf')}</scan:DocumentFormatExt>
    <scan:XResolution>{settings.get('resolution', 300)}</scan:XResolution>
    <scan:YResolution>{settings.get('resolution', 300)}</scan:YResolution>
    <scan:ColorMode>{settings.get('color_mode', 'RGB24')}</scan:ColorMode>
</scan:ScanSettings>"""

        try:
            headers = {"Content-Type": "text/xml"}
            response = requests.post(
                f"{self.base_url}/ScanJobs",
                data=scan_settings_xml,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()

            job_location = response.headers.get("Location")
            if job_location:
                return job_location
            else:
                raise ValueError("No job location returned")

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error creating scan job: {e}")

    def get_scan_document(self, job_location, max_retries=30, retry_delay=2):
        """Retrieve the scanned document with retry logic"""
        doc_url = f"{job_location}/NextDocument"

        for attempt in range(max_retries):
            try:
                response = requests.get(doc_url, timeout=60)
                response.raise_for_status()
                return response.content
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    else:
                        raise Exception(
                            f"Scan timed out after {max_retries * retry_delay} seconds"
                        )
                else:
                    raise Exception(f"Error retrieving scanned document: {e}")
            except requests.exceptions.RequestException as e:
                raise Exception(f"Error retrieving scanned document: {e}")

        raise Exception("Failed to retrieve scan")

    def delete_scan_job(self, job_location):
        """Delete the scan job"""
        try:
            requests.delete(job_location, timeout=10)
        except:
            pass


class PaperlessUploader:
    """Handle uploads to Paperless-ngx"""

    def __init__(self, paperless_url, api_token):
        self.paperless_url = paperless_url.rstrip("/")
        self.api_token = api_token
        self.headers = {"Authorization": f"Token {api_token}"}

    def upload_document(self, file_data, filename, title=None):
        """Upload document to Paperless-ngx"""
        try:
            upload_url = f"{self.paperless_url}/api/documents/post_document/"

            files = {"document": (filename, file_data, "application/pdf")}
            data = {}

            if title:
                data["title"] = title

            response = requests.post(
                upload_url, files=files, data=data, headers=self.headers, timeout=60
            )
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            raise Exception(f"Error uploading to Paperless-ngx: {e}")


def perform_scan(resolution=300, color_mode="RGB24", source=None, title=None):
    """Perform a scan operation"""
    # Initialize scanner
    scanner = ESCLScanner(SCANNER_IP)

    # Auto-detect ADF if source not specified
    if source is None:
        has_adf = scanner.get_scanner_capabilities()
        source = "Adf" if has_adf else "Platen"
        app.logger.info(f"Auto-detected source: {source}")

    # Prepare scan settings
    scan_settings = {
        "resolution": resolution,
        "color_mode": color_mode,
        "input_source": source,
        "format": "application/pdf",
        "intent": "Document",
        "width": 2550,
        "height": 3300,
    }

    # Create scan job
    job_location = scanner.create_scan_job(scan_settings)

    # Get scanned document
    document_data = scanner.get_scan_document(job_location)

    # Clean up scan job
    scanner.delete_scan_job(job_location)

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"scan_{timestamp}.pdf"

    # Upload to Paperless-ngx
    uploader = PaperlessUploader(PAPERLESS_URL, PAPERLESS_TOKEN)
    uploader.upload_document(document_data, filename, title=title)

    return {
        "success": True,
        "message": f"Scanned {len(document_data)} bytes and uploaded to Paperless",
        "filename": filename,
        "source": source,
    }


@app.route("/scan", methods=["GET", "POST"])
def scan():
    """Trigger a scan with optional parameters"""
    if request.method == "GET":
        # GET request with default settings
        resolution = int(request.args.get("resolution", 300))
        color_mode = request.args.get("color_mode", "RGB24")
        source = request.args.get("source")
        title = request.args.get("title")
    else:
        # POST request with JSON body
        data = request.get_json() or {}
        resolution = data.get("resolution", 300)
        color_mode = data.get("color_mode", "RGB24")
        source = data.get("source")
        title = data.get("title")

    try:
        result = perform_scan(resolution, color_mode, source, title)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/autoscan/enable", methods=["POST", "GET"])
def enable_autoscan():
    """Enable auto-scan mode"""
    global AUTO_SCAN_ENABLED
    AUTO_SCAN_ENABLED = True
    return (
        jsonify(
            {
                "success": True,
                "message": "Auto-scan enabled",
                "autoscan": AUTO_SCAN_ENABLED,
            }
        ),
        200,
    )


@app.route("/autoscan/disable", methods=["POST", "GET"])
def disable_autoscan():
    """Disable auto-scan mode"""
    global AUTO_SCAN_ENABLED
    AUTO_SCAN_ENABLED = False
    return (
        jsonify(
            {
                "success": True,
                "message": "Auto-scan disabled",
                "autoscan": AUTO_SCAN_ENABLED,
            }
        ),
        200,
    )


@app.route("/autoscan/status", methods=["GET"])
def autoscan_status():
    """Get auto-scan mode status"""
    return jsonify({"enabled": AUTO_SCAN_ENABLED}), 200


def autoscan_worker():
    """Background worker that checks for documents in ADF and scans automatically"""
    import threading

    def check_and_scan():
        global AUTO_SCAN_ENABLED
        scanner = ESCLScanner(SCANNER_IP)
        last_scan_time = 0

        while True:
            time.sleep(2)  # Check every 2 seconds

            if AUTO_SCAN_ENABLED:
                try:
                    # Check if document is loaded in ADF
                    if scanner.check_adf_loaded():
                        current_time = time.time()
                        # Debounce: wait 3 seconds before scanning
                        if current_time - last_scan_time > 3:
                            app.logger.info(
                                "Document detected in ADF, auto-scanning..."
                            )
                            result = perform_scan(
                                resolution=300, color_mode="RGB24", source="Adf"
                            )
                            app.logger.info(
                                f"Auto-scan completed: {result['filename']}"
                            )
                            last_scan_time = current_time
                except Exception as e:
                    app.logger.error(f"Auto-scan error: {e}")

    thread = threading.Thread(target=check_and_scan, daemon=True)
    thread.start()


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    # Validate configuration
    if not PAPERLESS_TOKEN:
        print(
            "WARNING: PAPERLESS_TOKEN not set. Please configure environment variables."
        )

    print(f"Starting eSCL Scanner API")
    print(f"Scanner IP: {SCANNER_IP}")
    print(f"Paperless URL: {PAPERLESS_URL}")
    print(f"API listening on: {API_HOST}:{API_PORT}")

    # Start auto-scan background worker
    autoscan_worker()

    # Run Flask app
    app.run(host=API_HOST, port=API_PORT, debug=False)
