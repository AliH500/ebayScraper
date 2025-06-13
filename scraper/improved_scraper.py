"""
Improved eBay Scraper with Enhanced Headers and Session Management
Uses advanced session handling to bypass eBay's protection systems.
"""

import logging # Imports the logging module for logging events and messages.
import time # Imports the time module for time-related functions like delays.
import re # Imports the regular expression module for pattern matching in strings.
import random # Imports the random module for generating random numbers (e.g., for delays).
from typing import Dict, List, Optional, Any # Imports type hints for better code readability and maintainability.
from urllib.parse import urljoin, quote_plus # Imports urljoin for constructing absolute URLs and quote_plus for URL encoding.

import requests # Imports the requests library for making HTTP requests.
from bs4 import BeautifulSoup # Imports BeautifulSoup for parsing HTML content.

from utils.rate_limiter import RateLimiter # Imports the custom RateLimiter utility.
from utils.user_agents import UserAgentRotator # Imports the custom UserAgentRotator utility.


class ImprovedEbayScraper:
    """Enhanced eBay scraper with better session management and headers"""
    
    def __init__(self, config):
        """Initializes the ImprovedEbayScraper with configuration."""
        self.config = config # Stores the configuration object.
        self.logger = logging.getLogger(__name__) # Gets a logger instance specific to this module.
        self.session = requests.Session() # Creates a new requests Session object for persistent connections and cookies.
        self.rate_limiter = RateLimiter(config.request_delay) # Initializes a RateLimiter with the delay specified in the config.
        self.user_agent_rotator = UserAgentRotator() # Initializes a UserAgentRotator to cycle through user agents.
        
        # Setup session with enhanced headers
        self._setup_enhanced_session() # Calls a private method to configure the session with enhanced headers.
        
        # eBay URLs
        self.base_url = "https://www.ebay.com" # Defines the base URL for eBay.
        self.search_url = "https://www.ebay.com/sch/i.html" # Defines the search results URL for eBay.
        
    def _setup_enhanced_session(self):
        """Configure the requests session with enhanced anti-detection measures"""
        # Enhanced headers to mimic real browser
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7', # Sets the Accept header to indicate preferred content types.
            'Accept-Language': 'en-US,en;q=0.9', # Sets the Accept-Language header to indicate preferred languages.
            'Accept-Encoding': 'gzip, deflate, br', # Sets the Accept-Encoding header to indicate preferred compression methods.
            'Connection': 'keep-alive', # Sets the Connection header to keep the connection alive.
            'Upgrade-Insecure-Requests': '1', # Indicates to the server that the client prefers an upgraded (HTTPS) connection.
            'Sec-Fetch-Dest': 'document', # Sets the Sec-Fetch-Dest header to 'document'.
            'Sec-Fetch-Mode': 'navigate', # Sets the Sec-Fetch-Mode header to 'navigate'.
            'Sec-Fetch-Site': 'none', # Sets the Sec-Fetch-Site header to 'none'.
            'Sec-Fetch-User': '?1', # Sets the Sec-Fetch-User header to '?1'.
            'Cache-Control': 'max-age=0', # Sets the Cache-Control header to prevent caching.
            'DNT': '1', # Sets the Do Not Track (DNT) header to '1'.
        })
        
        # Set proxy if configured
        if self.config.proxy_url: # Checks if a proxy URL is configured.
            self.session.proxies = { # Sets the proxies for the session.
                'http': self.config.proxy_url, # Sets the HTTP proxy.
                'https': self.config.proxy_url # Sets the HTTPS proxy.
            }
    
    def _get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch a page with enhanced session handling"""
        for attempt in range(retries): # Loops for a specified number of retry attempts.
            try:
                # Wait between requests
                self.rate_limiter.wait() # Calls the rate limiter to pause if necessary.
                
                # Rotate user agent for each request
                self.session.headers['User-Agent'] = self.user_agent_rotator.get_random_agent() # Sets a random user agent for the current request.
                
                # Add some randomness to make requests look more human
                time.sleep(random.uniform(0.5, 2.0)) # Adds a random delay between 0.5 and 2.0 seconds.
                
                self.logger.debug(f"Fetching URL: {url}") # Logs the URL being fetched at debug level.
                response = self.session.get(url, timeout=30) # Sends an HTTP GET request to the URL with a 30-second timeout.
                
                # Check response status
                if response.status_code == 200: # Checks if the HTTP status code is 200 (OK).
                    soup = BeautifulSoup(response.content, 'html.parser') # Parses the response content using BeautifulSoup.
                    
                    # Check if we got a valid page (not a security check)
                    page_text = soup.get_text().lower() # Gets all text from the page and converts to lowercase for checking.
                    if self._is_valid_page(page_text): # Calls a private method to check if the page is valid (not a security check).
                        self.rate_limiter.on_success() # Notifies the rate limiter of a successful request.
                        return soup # Returns the BeautifulSoup object.
                    else:
                        self.logger.warning("Got security check page, retrying with different approach...") # Logs a warning if a security check page is detected.
                        # Wait longer and try with different headers
                        time.sleep(random.uniform(5, 10)) # Waits for a longer random duration before retrying.
                        continue # Continues to the next retry attempt.
                
                elif response.status_code == 429: # Checks if the HTTP status code is 429 (Too Many Requests).
                    self.logger.warning("Rate limited, waiting longer...") # Logs a warning about being rate limited.
                    self.rate_limiter.on_failure("rate_limit") # Notifies the rate limiter of a rate limit failure.
                    time.sleep(random.uniform(10, 20)) # Waits for an even longer random duration.
                    continue # Continues to the next retry attempt.
                    
                else:
                    response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx).
                    
            except requests.RequestException as e: # Catches any exception related to requests.
                self.logger.warning(f"Request failed (attempt {attempt + 1}/{retries}): {str(e)}") # Logs a warning for failed requests.
                if attempt < retries - 1: # Checks if there are more retries left.
                    # Exponential backoff with randomness
                    wait_time = (2 ** attempt) + random.uniform(1, 3) # Calculates exponential backoff with randomness.
                    time.sleep(wait_time) # Waits for the calculated time.
                    # Try with fresh session on last retry
                    if attempt == retries - 2: # Checks if this is the second to last retry.
                        self._refresh_session() # Refreshes the session.
                
        self.logger.error(f"Failed to fetch page after {retries} attempts: {url}") # Logs an error if all retry attempts fail.
        self.rate_limiter.on_failure() # Notifies the rate limiter of a complete failure.
        return None # Returns None if the page could not be fetched.
    
    def _is_valid_page(self, page_text: str) -> bool:
        """Check if the page is valid (not a security check)"""
        security_indicators = [ # Defines a list of keywords indicating a security check or CAPTCHA page.
            'checking your browser', # Common phrase for browser checks.
            'security check', # General security check phrase.
            'blocked', # Indicates access is blocked.
            'access denied', # Indicates access is denied.
            'captcha', # Indicates a CAPTCHA challenge.
            'please wait while we check your browser' # Another common phrase for browser checks.
        ]
        
        return not any(indicator in page_text for indicator in security_indicators) # Returns True if none of the security indicators are found in the page text.
    
    def _refresh_session(self):
        """Refresh the session with new headers"""
        self.session.close() # Closes the current requests session.
        self.session = requests.Session() # Creates a new requests Session object.
        self._setup_enhanced_session() # Re-configures the new session with enhanced headers.
        self.logger.debug("Session refreshed") # Logs that the session has been refreshed.
    
    def scrape_search_results(self, search_query: str, max_pages: int = 1, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape eBay search results with enhanced handling"""
        all_items = [] # Initializes an empty list to store all scraped items.
        
        for page in range(1, max_pages + 1): # Iterates through the specified number of pages.
            self.logger.info(f"Scraping page {page} of search results...") # Logs the current page being scraped.
            
            # Build search URL with proper encoding
            search_params = { # Defines search parameters for URL construction.
                '_nkw': search_query, # The search keyword.
                '_pgn': page, # The page number.
                '_skc': 0, # Unknown parameter, often seen in eBay URLs.
                'rt': 'nc', # Real-time search.
                '_from': 'R40' # Source parameter.
            }
            
            # Construct URL manually to avoid encoding issues
            search_url = f"{self.search_url}?_nkw={quote_plus(search_query)}&_pgn={page}&_skc=0&rt=nc&_from=R40" # Constructs the full search URL, ensuring proper encoding of the search query.
            
            soup = self._get_page(search_url) # Fetches the search results page and gets the BeautifulSoup object.
            if not soup: # Checks if the page fetching was unsuccessful.
                self.logger.warning(f"Failed to fetch search page {page}") # Logs a warning for failed page fetch.
                continue # Continues to the next page in the loop.
            
            # Extract product links from search results
            product_links = self._extract_product_links(soup) # Extracts product links using the primary method.
            
            if not product_links: # Checks if no product links were found.
                self.logger.warning(f"No product links found on page {page}") # Logs a warning if no links are found.
                # Try alternative extraction method
                product_links = self._extract_product_links_alternative(soup) # Attempts to extract product links using an alternative method.
                
            if not product_links: # Checks again if product links are still not found after the alternative method.
                self.logger.warning(f"Still no products found on page {page}, moving to next page") # Logs a warning and moves to the next page.
                continue # Continues to the next page.
            
            self.logger.info(f"Found {len(product_links)} products on page {page}") # Logs the number of products found on the current page.
            
            # Extract data directly from search results
            search_items = self._extract_search_item_data(soup) # Extracts item data directly from the search results page HTML.
            
            for i, item_data in enumerate(search_items): # Iterates through each extracted item's data.
                if max_items and len(all_items) >= max_items: # Checks if the maximum number of items to scrape has been reached.
                    self.logger.info(f"Reached maximum items limit: {max_items}") # Logs that the item limit has been reached.
                    return all_items # Returns the list of all collected items.
                
                if item_data: # Checks if valid item data was extracted.
                    all_items.append(item_data) # Appends the item data to the list of all items.
                    self.logger.info(f"Extracted item {len(all_items)}: {item_data.get('title', 'Unknown')[:50]}...") # Logs a brief summary of the extracted item.
                else:
                    self.logger.warning(f"Failed to extract item data from search results") # Logs a warning if item data extraction failed.
        
        return all_items # Returns the complete list of scraped items.
    
    def _extract_product_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract product URLs from search results page"""
        links = [] # Initializes an empty list to store product links.
        
        # Multiple selectors for different eBay layouts
        selectors = [ # Defines a list of CSS selectors to find product links.
            '.s-item__link', # Primary selector for item links.
            '.s-item .s-item__title a', # Selector for title links within items.
            '.it-ttl a', # Alternative title link selector.
            '.vip a', # Another alternative link selector.
            'a[href*="/itm/"]', # Generic selector for links containing '/itm/'.
            '.s-item h3 a' # Selector for links within h3 tags inside items.
        ]
        
        for selector in selectors: # Iterates through each defined CSS selector.
            elements = soup.select(selector) # Selects all elements matching the current selector.
            for element in elements: # Iterates through each found element.
                href = element.get('href') # Gets the 'href' attribute (URL) of the element.
                if href and '/itm/' in href: # Checks if href exists and contains '/itm/' (indicating an item page).
                    # Convert to string if needed
                    href_str = str(href) if href else "" # Ensures href is a string.
                    # Clean up the URL
                    if href_str.startswith('//'): # Checks if the URL starts with '//'.
                        href_str = 'https:' + href_str # Prefixes with 'https:' to make it an absolute URL.
                    elif href_str.startswith('/'): # Checks if the URL starts with '/'.
                        href_str = self.base_url + href_str # Joins with the base URL to make it absolute.
                    
                    # Remove tracking parameters
                    clean_url = self._clean_ebay_url(href_str) # Cleans the URL by removing tracking parameters.
                    if clean_url not in links and 'ebay.com' in clean_url: # Checks if the cleaned URL is unique and contains 'ebay.com'.
                        links.append(clean_url) # Adds the cleaned URL to the list.
        
        return links[:50] # Returns a maximum of 50 unique links per page.
    
    def _extract_search_item_data(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract product data directly from search results page"""
        items = [] # Initializes an empty list to store dictionaries of item data.
        
        # Find all search result items
        item_containers = soup.select('.s-item') # Selects all elements with the class 's-item', representing individual search result items.
        
        for container in item_containers: # Iterates through each item container.
            try:
                # Skip sponsored items or ads
                if container.select('.SPONSORED'): # Checks if the container has a '.SPONSORED' class, indicating an ad.
                    continue # Skips to the next item if it's a sponsored ad.
                
                # Extract title
                title_element = container.select_one('.s-item__title span') # Selects the title element.
                title = title_element.get_text(strip=True) if title_element else None # Extracts title text, strips whitespace, or sets to None.
                
                # Extract price
                price_element = container.select_one('.s-item__price .notranslate') # Selects the price element.
                price = price_element.get_text(strip=True) if price_element else None # Extracts price text, strips whitespace, or sets to None.
                
                # Extract URL
                link_element = container.select_one('.s-item__link') # Selects the link element for the item.
                url = link_element.get('href') if link_element else None # Gets the 'href' attribute (URL).
                if url: # Checks if a URL was found.
                    url = str(url) # Ensures the URL is a string.
                    url = self._clean_ebay_url(url) # Cleans the URL.
                
                # Extract image
                img_element = container.select_one('.s-item__image img') # Selects the image element.
                image_url = img_element.get('src') if img_element else None # Gets the 'src' attribute of the image.
                if image_url: # Checks if an image URL was found.
                    image_url = str(image_url) # Ensures the image URL is a string.
                    if image_url.startswith('//'): # Checks if the image URL starts with '//'.
                        image_url = 'https:' + image_url # Prefixes with 'https:' to make it an absolute URL.
                
                # Extract condition (if available in search results)
                condition_element = container.select_one('.SECONDARY_INFO') # Selects an element that might contain condition info.
                condition = condition_element.get_text(strip=True) if condition_element else None # Extracts condition text, strips whitespace, or sets to None.
                
                # Extract shipping info
                shipping_element = container.select_one('.s-item__shipping') # Selects the shipping info element.
                shipping = shipping_element.get_text(strip=True) if shipping_element else None # Extracts shipping text, strips whitespace, or sets to None.
                
                # Extract sold quantity from search results if available
                sold_text = container.get_text() # Gets all text from the item container.
                quantity_sold = None # Initializes quantity_sold to None.
                sold_match = re.search(r'(\d+)\s+sold', sold_text, re.IGNORECASE) # Searches for a pattern like "X sold".
                if sold_match: # Checks if a match was found.
                    try:
                        quantity_sold = int(sold_match.group(1)) # Converts the matched number to an integer.
                    except ValueError: # Catches if the conversion fails.
                        pass # Continues without setting quantity_sold.
                
                # Only add if we have essential data
                if title and price and url: # Ensures that title, price, and URL are present.
                    item_data = { # Creates a dictionary for the extracted item data.
                        'listing_url': url, # Item's listing URL.
                        'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'), # Timestamp of scraping.
                        'primary_image_url': image_url, # URL of the primary image.
                        'title': title, # Product title.
                        'price': price, # Product price.
                        'condition': condition, # Product condition.
                        'quantity_sold': quantity_sold, # Quantity of items sold.
                        'shipping_info': shipping, # Shipping information.
                        'item_specifics': {},  # Item specifics are not usually available in search results, so an empty dict.
                        'description': None  # Description is not usually available in search results, so None.
                    }
                    items.append(item_data) # Appends the collected item data to the list.
                    
            except Exception as e:
                self.logger.debug(f"Error extracting item data: {str(e)}") # Logs a debug message if an error occurs during item data extraction.
                continue # Continues to the next item container.
        
        return items # Returns the list of extracted items.
    
    def _extract_product_links_alternative(self, soup: BeautifulSoup) -> List[str]:
        """Alternative method to extract product links"""
        links = [] # Initializes an empty list to store product links.
        
        # Look for any links containing item IDs
        all_links = soup.find_all('a', href=True) # Finds all <a> tags with an 'href' attribute.
        for link in all_links: # Iterates through each found link.
            href = link['href'] # Gets the 'href' attribute value.
            # Look for eBay item URLs
            if '/itm/' in href and 'ebay.com' in href: # Checks if the URL contains '/itm/' and 'ebay.com'.
                clean_url = self._clean_ebay_url(href) # Cleans the URL.
                if clean_url not in links: # Checks for uniqueness.
                    links.append(clean_url) # Adds the cleaned URL to the list.
        
        return links[:50] # Returns a maximum of 50 unique links.
    
    def _clean_ebay_url(self, url: str) -> str:
        """Clean eBay URL by removing tracking parameters"""
        # Extract the item ID and create a clean URL
        match = re.search(r'/itm/(\d+)', url) # Searches for the item ID (digits after '/itm/').
        if match: # If a match is found.
            item_id = match.group(1) # Extracts the item ID.
            return f"https://www.ebay.com/itm/{item_id}" # Constructs a clean, simplified eBay item URL.
        return url # Returns the original URL if no item ID pattern is found.
    
    def scrape_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed information from a product page"""
        soup = self._get_page(product_url) # Fetches the product page and gets the BeautifulSoup object.
        if not soup: # If the page couldn't be fetched.
            return None # Returns None.
        
        try:
            product_data = { # Creates a dictionary to hold product details.
                'listing_url': product_url, # The URL of the product listing.
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'), # Timestamp of when the data was scraped.
                'primary_image_url': self._extract_primary_image(soup), # Extracts the primary image URL.
                'title': self._extract_title(soup), # Extracts the product title.
                'price': self._extract_price(soup), # Extracts the product price.
                'condition': self._extract_condition(soup), # Extracts the product condition.
                'quantity_sold': self._extract_quantity_sold(soup), # Extracts the quantity sold.
                'item_specifics': self._extract_item_specifics(soup), # Extracts the item specifics.
                'description': self._extract_description(soup) # Extracts the product description.
            }
            
            return product_data # Returns the dictionary of product data.
            
        except Exception as e:
            self.logger.error(f"Error scraping product details from {product_url}: {str(e)}") # Logs an error if scraping product details fails.
            return None # Returns None due to an error.
    
    def _extract_primary_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract primary product image URL"""
        selectors = [ # Defines a list of CSS selectors to find the primary image.
            '#icImg', # Common ID for the main image.
            '#image', # Another common ID for the main image.
            '.img img', # Generic image within a container.
            '.u-photo img', # Image within a microformat photo container.
            '[data-zoom-src]', # Image with a data-zoom-src attribute.
            '.img640 img', # Image within a 640px image container.
            'img[id*="image"]' # Any img tag with an ID containing "image".
        ]
        
        for selector in selectors: # Iterates through each selector.
            img = soup.select_one(selector) # Selects the first element matching the selector.
            if img: # If an image element is found.
                src = img.get('src') or img.get('data-zoom-src') or img.get('data-src') # Tries to get the 'src', 'data-zoom-src', or 'data-src' attribute.
                if src and 'http' in src and 'data:' not in src: # Checks if src exists, contains 'http', and is not a base64 data URI.
                    # Clean up image URL
                    if src.startswith('//'): # If the URL is protocol-relative.
                        src = 'https:' + src # Prefixes with 'https:' to make it absolute.
                    return src # Returns the cleaned image source URL.
        
        return None # Returns None if no primary image URL is found.
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product title"""
        selectors = [ # Defines a list of CSS selectors to find the product title.
            '#x-title-label-lbl', # Common ID for the title label.
            '.x-title-label-lbl', # Class for the title label.
            'h1[id*="title"]', # H1 tag with an ID containing "title".
            '.it-ttl', # Class for item title.
            'h1', # Generic H1 tag.
            '.x-title-label' # Another class for title label.
        ]
        
        for selector in selectors: # Iterates through each selector.
            element = soup.select_one(selector) # Selects the first element matching the selector.
            if element: # If an element is found.
                title = element.get_text(strip=True) # Gets the text content and strips whitespace.
                if title and len(title) > 5 and 'checking your browser' not in title.lower(): # Checks if the title is valid and not a security check message.
                    return title # Returns the extracted title.
        
        return None # Returns None if no valid title is found.
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product price"""
        selectors = [ # Defines a list of CSS selectors to find the product price.
            '.price .notranslate', # Common selector for price.
            '[data-testid="price"] .notranslate', # Price element with a data-testid attribute.
            '.u-price .notranslate', # Price within a 'u-price' container.
            '.display-price', # Selector for displayed price.
            '.bin-price .notranslate', # Buy-It-Now price.
            '.auction-price .notranslate', # Auction price.
            '.price-current', # Current price.
            '[class*="price"] .notranslate' # Any element with 'price' in its class and 'notranslate'.
        ]
        
        for selector in selectors: # Iterates through each selector.
            element = soup.select_one(selector) # Selects the first element matching the selector.
            if element: # If an element is found.
                price_text = element.get_text(strip=True) # Gets the text content and strips whitespace.
                # Look for currency symbols
                if price_text and any(symbol in price_text for symbol in ['$', '€', '£', 'USD', 'EUR', 'GBP']): # Checks if the price text contains common currency symbols.
                    return price_text # Returns the extracted price text.
        
        return None # Returns None if no valid price is found.
    
    def _extract_condition(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract item condition"""
        # Look for condition in item specifics first
        page_text = soup.get_text().lower() # Gets all text from the page and converts to lowercase.
        
        condition_patterns = [ # Defines regular expression patterns to find the item condition.
            r'condition[^:]*:?\s*(new|used|refurbished|open box|for parts|pre-owned)', # Pattern for "condition: [value]".
            r'item condition[^:]*:?\s*(new|used|refurbished|open box|for parts|pre-owned)' # Pattern for "item condition: [value]".
        ]
        
        for pattern in condition_patterns: # Iterates through each condition pattern.
            match = re.search(pattern, page_text, re.IGNORECASE) # Searches for the pattern in the page text (case-insensitive).
            if match: # If a match is found.
                return match.group(1).title() # Returns the captured condition value with the first letter capitalized.
        
        return None # Returns None if no condition is found.
    
    def _extract_quantity_sold(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract quantity sold (very important field)"""
        page_text = soup.get_text() # Gets all text from the page.
        
        sold_patterns = [ # Defines regular expression patterns to find the quantity sold.
            r'(\d+[\d,]*)\s*sold', # Pattern for "X sold".
            r'sold:\s*(\d+[\d,]*)', # Pattern for "sold: X".
            r'(\d+[\d,]*)\s*vendus?', # Pattern for French "X vendus".
            r'quantity\s*sold:\s*(\d+[\d,]*)' # Pattern for "quantity sold: X".
        ]
        
        for pattern in sold_patterns: # Iterates through each sold quantity pattern.
            matches = re.findall(pattern, page_text, re.IGNORECASE) # Finds all occurrences of the pattern.
            if matches: # If any matches are found.
                try:
                    # Get the highest number found
                    quantities = [int(match.replace(',', '')) for match in matches] # Converts matched strings to integers, removing commas.
                    return max(quantities) # Returns the highest quantity found.
                except ValueError: # Catches if conversion to int fails.
                    continue # Continues to the next pattern.
        
        return None # Returns None if no quantity sold is found.
    
    def _extract_item_specifics(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract item specifics (key-value pairs)"""
        specifics = {} # Initializes an empty dictionary to store item specifics.
        
        # Multiple selectors for different layouts
        selectors = [ # Defines a list of CSS selectors for item specifics containers.
            '.itemAttr', # Common class for item attributes.
            '.item-specifics tr', # Rows within item specifics tables.
            '[data-testid="item-specifics"] tr' # Rows within item specifics table identified by data-testid.
        ]
        
        for selector in selectors: # Iterates through each selector.
            rows = soup.select(selector) # Selects all elements matching the current selector.
            for row in rows: # Iterates through each row.
                # Try to extract key-value pairs
                cells = row.find_all(['td', 'th', 'div']) # Finds all 'td', 'th', or 'div' elements within the row.
                if len(cells) >= 2: # Checks if there are at least two cells for a key-value pair.
                    key = cells[0].get_text(strip=True).rstrip(':') # Extracts the key text, strips whitespace, and removes trailing colon.
                    value = cells[1].get_text(strip=True) # Extracts the value text and strips whitespace.
                    if key and value and len(key) < 50 and len(value) < 200: # Validates key and value length.
                        specifics[key] = value # Adds the key-value pair to the dictionary.
        
        # Alternative: look for definition lists
        dl_elements = soup.select('dl') # Selects all <dl> (definition list) elements.
        for dl in dl_elements: # Iterates through each definition list.
            dt_elements = dl.find_all('dt') # Finds all <dt> (definition term) elements.
            dd_elements = dl.find_all('dd') # Finds all <dd> (definition description) elements.
            
            for dt, dd in zip(dt_elements, dd_elements): # Iterates through paired dt and dd elements.
                key = dt.get_text(strip=True).rstrip(':') # Extracts the key from <dt>.
                value = dd.get_text(strip=True) # Extracts the value from <dd>.
                if key and value and len(key) < 50 and len(value) < 200: # Validates key and value length.
                    specifics[key] = value # Adds the key-value pair to the dictionary.
        
        return specifics # Returns the dictionary of item specifics.
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract full description text"""
        selectors = [ # Defines a list of CSS selectors to find the product description.
            '#desc_div', # Common ID for description div.
            '.item-description', # Class for item description.
            '[data-testid="description"]', # Description identified by data-testid.
            '.description', # Generic description class.
            '#item_description' # Another common ID for item description.
        ]
        
        for selector in selectors: # Iterates through each selector.
            element = soup.select_one(selector) # Selects the first element matching the selector.
            if element: # If an element is found.
                # Get text content, preserving some structure
                description = element.get_text(separator='\n', strip=True) # Gets the text content, preserving line breaks, and stripping whitespace.
                if description and len(description) > 20: # Checks if the description is valid and reasonably long.
                    return description[:5000] # Returns the first 5000 characters of the description.
        
        return None # Returns None if no valid description is found.