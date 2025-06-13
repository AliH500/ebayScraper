# eBay Product Scraper

A robust, VPS-compatible tool for scraping detailed product information from eBay listings. This scraper is designed for research and data analysis purposes, with built-in rate limiting, error handling, and multiple export formats.

## Features

### Core Functionality
- **Custom Search Queries**: Accept user-defined search terms, categories, and filters
- **Deep Listing Parsing**: Navigate from search results to individual product pages
- **Comprehensive Data Extraction**: Collect listing URL, images, title, price, condition, quantity sold, item specifics, and descriptions
- **Pagination Support**: Automatically scrape multiple pages of search results
- **Multiple Export Formats**: Export data to CSV, JSON, and Excel formats

### Advanced Features
- **Rate Limiting**: Respectful crawling with adjustable delays
- **User Agent Rotation**: Mimic different browsers to avoid detection
- **Error Handling**: Graceful handling of timeouts, missing fields, and blocked requests
- **Logging System**: Comprehensive logging for monitoring and debugging
- **Proxy Support**: Optional proxy configuration for additional anonymization
- **VPS Compatible**: Designed to run on Linux/Ubuntu VPS environments

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Required Dependencies
Install the required packages using pip:

```bash
pip install requests beautifulsoup4 pandas python-dotenv fake-useragent openpyxl lxml
