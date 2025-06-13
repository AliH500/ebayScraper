#!/usr/bin/env python3
"""
eBay Product Scraper - Dual Mode (CLI + Web Interface)
"""
import threading
import webbrowser
import time
import os
import platform
from pathlib import Path
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash
from threading import Lock
from scraper.selenium_scraper import SeleniumEbayScraper
from scraper.data_exporter import DataExporter
from scraper.config import Config

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for flash messaging

from flask import Flask, request, jsonify, send_from_directory
import threading
import time
import os

# ... (your existing imports and setup) ...

#Global variables with thread safety
scraping_status = {
    "running": False,
    "current_item": "",
    "completed_items": 0,
    "total_items": 0,
    "results": [],
    "errors": []
}
status_lock = Lock()

import os
import platform
from pathlib import Path

def get_default_download_dir():
    """Returns the OS-specific Downloads folder path."""
    if platform.system() == "Windows":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                downloads_path = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
                return downloads_path
        except Exception:
            return str(Path.home() / "Downloads")
    else:
        # For macOS/Linux
        return str(Path.home() / "Downloads")


def scrape_background(form_data):
    global scraping_status

    # Step 1: Set initial status
    with status_lock:
        scraping_status.update({
            "running": True,
            "completed_items": 0,
            "total_items": 0,
            "results": [],
            "form_data": form_data,
            "last_updated": time.time()
        })

    try:
        # Step 2: Run scraping (do NOT hold lock here!)
        config = Config()


        scraper = SeleniumEbayScraper(config)

        search_query = form_data.get("search_query")
        pages = int(form_data.get("pages", 1))
        max_items = form_data.get("max_items")

        results = scraper.scrape_search_results(
            search_query=search_query,
            max_pages=pages,
            max_items=max_items
        )


        print(f"✅ Scraped {len(results)} items.")

        # Step 3: Safely update status after scraping
        with status_lock:
            scraping_status.update({
                "running": False,
                "completed_items": len(results),
                "total_items": len(results),
                "results": results,
                "last_updated": time.time()
            })
    except Exception as e:
        print("❌ Scraping failed:", e)
        with status_lock:
            scraping_status.update({
                "running": False,
                "error": str(e),
                "last_updated": time.time()
            })

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    data = request.json
    search_query = data.get('search_query')
    pages = data.get('pages', 1)
    max_items = data.get('max_items')
    use_selenium = data.get('use_selenium', True)

    if not search_query:
        return jsonify({"error": "Search query is required"}), 400

    # Store form data in scraping_status before starting thread
    scraping_status.update({
        "form_data": {
            "search_query": search_query,
            "pages": pages,
            "max_items": max_items,
            "use_selenium": use_selenium
        },
        "running": True,
        "current_item": "Initializing",
        "completed_items": 0,
        "total_items": 0,
        "results": [],
        "errors": [],
        "start_time": datetime.now().isoformat()
    })

    thread = threading.Thread(target=scrape_background, args=(data,))
    thread.start()

    return jsonify({"message": "Scraping started", "status_url": url_for('api_status', _external=True)})

# API route for checking status
@app.route('/api/status', methods=['GET'])
def api_status():
    print("🟡 /api/status hit — trying to acquire lock")
    with status_lock:
        print("🟢 /api/status acquired lock")

        # Timeout checker
        if time.time() - scraping_status.get('last_updated', 0) > 30:
            print("⚠️ Status too old — session expired")
            return jsonify({
                "error": "Scraping session expired",
                "running": False
            })

        return jsonify(scraping_status)



# API route for test scraping
@app.route('/api/test-scrape', methods=['POST'])
def api_test_scrape():
    data = request.json
    search_query = data.get('search_query')
    use_selenium = data.get('use_selenium', False)

    if not search_query:
        return jsonify({"error": "Search query is required"}), 400

    try:
        config = Config()
        config.request_delay = 1.0
        config.use_selenium = use_selenium

        scraper = SeleniumEbayScraper(config)
        test_data = scraper.scrape_search_results(
            search_query=search_query,
            max_pages=1,
            max_items=2  # Limit to 2 items for testing
        )

        return jsonify({
            "message": f"Test scrape completed ({len(test_data)} items)",
            "results": test_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API route for stopping a scrape
@app.route('/api/stop', methods=['POST'])
def api_stop():
    scraping_status["running"] = False
    return jsonify({"message": "Scraping stopped"})

# API route for exporting data
@app.route('/api/export', methods=['POST'])
def api_export():
    data = request.json
    output_format = data.get('format', 'both')
    output_dir = get_default_download_dir()


    if not scraping_status["results"]:
        return jsonify({"error": "No data to export"}), 400

    try:
        output_dir = Path(output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        exporter = DataExporter(output_dir, f"ebay_export_{timestamp}")

        files = []
        if output_format in ['csv', 'both']:
            csv_file = exporter.export_to_csv(scraping_status["results"])
            files.append(str(csv_file))
        if output_format in ['json', 'both']:
            json_file = exporter.export_to_json(scraping_status["results"])
            files.append(str(json_file))

        return jsonify({
            "message": "Export successful",
            "files": files
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API route for downloading files
@app.route('/api/download/<path:filename>', methods=['GET'])
@app.route('/api/download/<path:filename>', methods=['GET'])
def api_download(filename):
    download_dir = get_default_download_dir()
    return send_from_directory(download_dir, filename, as_attachment=True)


def setup_logging(log_level='INFO'):
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'ebay_scraper_{timestamp}.log'
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def run_cli():
    parser = argparse.ArgumentParser(description='eBay Product Scraper CLI')
    parser.add_argument('search_query', help='Search query for eBay products')
    parser.add_argument('--pages', type=int, default=1)
    parser.add_argument('--delay', type=float, default=2.0)
    parser.add_argument('--output-format', choices=['csv', 'json', 'both'], default='both')
    parser.add_argument('--output-dir', default='output')
    parser.add_argument('--max-items', type=int)
    parser.add_argument('--download-images', action='store_true')
    parser.add_argument('--proxy')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    parser.add_argument('--config')

    args = parser.parse_args()
    logger = setup_logging(args.log_level)
    logger.info("Starting eBay scraper...")

    try:
        config = Config(config_file=args.config)
        config.request_delay = args.delay
        if args.proxy:
            config.proxy_url = args.proxy
        config.download_images = args.download_images

        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)

        scraper = SeleniumEbayScraper(config)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        exporter = DataExporter(output_dir, f"ebay_scrape_{timestamp}")

        scraped_data = scraper.scrape_search_results(
            search_query=args.search_query,
            max_pages=args.pages,
            max_items=args.max_items
        )

        if not scraped_data:
            logger.warning("No data scraped.")
            return

        if args.output_format in ['csv', 'both']:
            csv_file = exporter.export_to_csv(scraped_data)
            logger.info(f"CSV saved: {csv_file}")

        if args.output_format in ['json', 'both']:
            json_file = exporter.export_to_json(scraped_data)
            logger.info(f"JSON saved: {json_file}")

        logger.info("Scraping completed successfully!")

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}", exc_info=True)
        sys.exit(1)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        search_query = request.form.get("searchQuery")
        pages = int(request.form.get("pages", 1))
        delay = float(request.form.get("delay", 2.0))
        output_format = request.form.get("output_format", "both")
        download_images = "download_images" in request.form

        logger = setup_logging()
        try:
            config = Config()
            config.request_delay = delay
            config.download_images = download_images

            output_dir = Path("output")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            exporter = DataExporter(output_dir, f"ebay_scrape_{timestamp}")
            scraper = SeleniumEbayScraper(config)

            scraped_data = scraper.scrape_search_results(
                search_query=search_query,
                max_pages=pages
            )

            if not scraped_data:
                flash("No data found for the query.", "warning")
                return redirect(url_for("index"))

            if output_format in ["csv", "both"]:
                exporter.export_to_csv(scraped_data)
            if output_format in ["json", "both"]:
                exporter.export_to_json(scraped_data)

            flash(f"Scraped {len(scraped_data)} items successfully!", "success")
        except Exception as e:
            flash(f"An error occurred: {e}", "danger")
        return redirect(url_for("index"))

    return render_template("index.html")

if __name__ == "__main__":
    # Start the browser after the server is running
    def open_browser():
        time.sleep(1)  # Wait for Flask to start
        webbrowser.open("http://127.0.0.1:5000/")

    threading.Thread(target=open_browser).start()

    # Run the Flask server
    app.run(debug=False)