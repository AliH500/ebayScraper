"""
Configuration Module
Handles configuration settings for the eBay scraper.
"""

# Import required standard library modules
import os  # For operating system dependent functionality
import logging  # For logging configuration
from pathlib import Path  # For object-oriented filesystem paths
from typing import Optional  # For type hints
from dotenv import load_dotenv  # For loading environment variables


class Config:
    """Configuration management for eBay scraper"""
    
    def __init__(self, config_file: Optional[str] = None):
        # Initialize logger for this class
        self.logger = logging.getLogger(__name__)
        
        # Load environment variables from specified file or default .env
        if config_file and Path(config_file).exists():
            load_dotenv(config_file)  # Load from specified config file
        else:
            load_dotenv()  # Load from default .env file
        
        # Request settings with default values
        self.request_delay = float(os.getenv('REQUEST_DELAY', '2.0'))  # Delay between requests
        self.blocked_delay = float(os.getenv('BLOCKED_DELAY', '30.0'))  # Delay when blocked
        self.request_timeout = int(os.getenv('REQUEST_TIMEOUT', '30'))  # Request timeout
        self.max_retries = int(os.getenv('MAX_RETRIES', '3'))  # Max retry attempts
        
        # Proxy configuration
        self.proxy_url = os.getenv('PROXY_URL')  # Proxy server URL
        # Whether to rotate between multiple proxies
        self.proxy_rotation = os.getenv('PROXY_ROTATION', 'false').lower() == 'true'
        
        # User agent configuration
        # Whether to rotate user agents
        self.rotate_user_agents = os.getenv('ROTATE_USER_AGENTS', 'true').lower() == 'true'
        self.custom_user_agent = os.getenv('CUSTOM_USER_AGENT')  # Fixed user agent if specified
        
        # Output configuration
        self.default_output_dir = os.getenv('OUTPUT_DIR', 'output')  # Default output directory
        # Whether to download product images
        self.download_images = os.getenv('DOWNLOAD_IMAGES', 'false').lower() == 'true'
        self.image_dir = os.getenv('IMAGE_DIR', 'images')  # Directory for downloaded images
        
        # Scraping limits
        self.default_max_pages = int(os.getenv('DEFAULT_MAX_PAGES', '5'))  # Max pages to scrape
        self.default_max_items = os.getenv('DEFAULT_MAX_ITEMS')  # Max items to scrape
        if self.default_max_items:
            self.default_max_items = int(self.default_max_items)  # Convert to int if specified
        
        # Search settings
        # Default filters for search queries
        self.default_search_filters = os.getenv('DEFAULT_SEARCH_FILTERS', '')
        # Default sort order for search results
        self.search_sort_order = os.getenv('SEARCH_SORT_ORDER', 'BestMatch')
        
        # Data validation settings
        # Whether to validate scraped data
        self.validate_data = os.getenv('VALIDATE_DATA', 'true').lower() == 'true'
        # Whether to skip invalid items
        self.skip_invalid_items = os.getenv('SKIP_INVALID_ITEMS', 'true').lower() == 'true'
        
        # Logging configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')  # Default log level
        self.log_dir = os.getenv('LOG_DIR', 'logs')  # Directory for log files
        # Whether to enable file logging
        self.enable_file_logging = os.getenv('ENABLE_FILE_LOGGING', 'true').lower() == 'true'
        
        # Advanced settings
        # Number of concurrent requests
        self.concurrent_requests = int(os.getenv('CONCURRENT_REQUESTS', '1'))
        # Whether to respect robots.txt
        self.respect_robots_txt = os.getenv('RESPECT_ROBOTS_TXT', 'true').lower() == 'true'
        
        # Validate the loaded configuration
        self._validate_config()
    
    def _validate_config(self):
        """Validate configuration values to ensure they are reasonable"""
        # Validate request delay values
        if self.request_delay < 0.1:
            self.logger.warning("Request delay is very low, this may cause rate limiting")
        
        if self.request_delay > 60:
            self.logger.warning("Request delay is very high, scraping will be slow")
        
        # Validate request timeout
        if self.request_timeout < 5:
            self.logger.warning("Request timeout is very low, may cause failed requests")
        
        # Validate retry count
        if self.max_retries > 10:
            self.logger.warning("Max retries is very high, may cause long delays")
        
        # Validate concurrent requests setting
        if self.concurrent_requests > 5:
            self.logger.warning("High concurrent requests may trigger rate limiting")
    
    def get_search_params(self) -> dict:
        """Get default search parameters as a dictionary"""
        params = {}  # Initialize empty parameters dictionary
        
        # Handle search sort order if specified
        if self.search_sort_order:
            sort_mapping = {
                'BestMatch': 'Best+Match',
                'PriceLowest': 'PricePlusShippingLowest',
                'PriceHighest': 'PricePlusShippingHighest',
                'TimeLeft': 'EndTimeSoonest',
                'NewlyListed': 'StartTimeNewest',
                'DistanceNearest': 'DistanceNearest'
            }
            if self.search_sort_order in sort_mapping:
                params['_sop'] = sort_mapping[self.search_sort_order]
        
        # Parse and add any default search filters
        if self.default_search_filters:
            # Parse filters from string (format: "key1=value1,key2=value2")
            for filter_pair in self.default_search_filters.split(','):
                if '=' in filter_pair:
                    key, value = filter_pair.strip().split('=', 1)
                    params[key.strip()] = value.strip()
        
        return params  # Return the populated parameters
    
    def get_headers(self) -> dict:
        """Get default HTTP request headers"""
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add custom user agent if specified
        if self.custom_user_agent:
            headers['User-Agent'] = self.custom_user_agent
        
        return headers  # Return headers dictionary
    
    def to_dict(self) -> dict:
        """Export configuration as a dictionary for serialization"""
        return {
            'request_delay': self.request_delay,
            'blocked_delay': self.blocked_delay,
            'request_timeout': self.request_timeout,
            'max_retries': self.max_retries,
            'proxy_url': self.proxy_url,
            'proxy_rotation': self.proxy_rotation,
            'rotate_user_agents': self.rotate_user_agents,
            'custom_user_agent': self.custom_user_agent,
            'default_output_dir': self.default_output_dir,
            'download_images': self.download_images,
            'image_dir': self.image_dir,
            'default_max_pages': self.default_max_pages,
            'default_max_items': self.default_max_items,
            'search_sort_order': self.search_sort_order,
            'validate_data': self.validate_data,
            'skip_invalid_items': self.skip_invalid_items,
            'log_level': self.log_level,
            'log_dir': self.log_dir,
            'concurrent_requests': self.concurrent_requests,
            'respect_robots_txt': self.respect_robots_txt
        }
    
    def __str__(self):
        """Return a human-readable string representation of the configuration"""
        return f"EbayScraper Config (delay: {self.request_delay}s, retries: {self.max_retries})"