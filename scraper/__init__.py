# Module-level documentation describing the package's primary purpose
"""eBay Scraper Package
A robust tool for scraping eBay product listings with rate limiting and
data export capabilities."""

__version__ = "1.0.0"
__author__ = "eBay Scraper Team"

# Import the main scraper class from the ebay_scraper module
from .ebay_scraper import EbayScraper
# Import the data export functionality from the data_exporter module
from .data_exporter import DataExporter
# Import configuration management from the config module
from .config import Config

# Define public API by listing all symbols that should be imported when using 'from package import *'
__all__ = ["EbayScraper", "DataExporter", "Config"]