"""
Selenium-based eBay Scraper with Enhanced Anti-Detection
Uses real browser automation to bypass eBay's protection systems.
"""

import logging # Imports the logging module for logging events.
import time # Imports the time module for time-related functions like delays.
import re # Imports the regular expression module for pattern matching.
from typing import Dict, List, Optional, Any # Imports type hints for better code readability and maintainability.
from urllib.parse import urljoin # Imports urljoin for constructing full URLs.

from selenium import webdriver # Imports the selenium webdriver for browser automation.
from selenium.webdriver.common.by import By # Imports By class for locating elements using different strategies.
from selenium.webdriver.support.ui import WebDriverWait # Imports WebDriverWait for explicit waits.
from selenium.webdriver.support import expected_conditions as EC # Imports expected_conditions for common conditions to wait for.
from selenium.webdriver.chrome.options import Options # Imports Options to configure Chrome browser settings.
from selenium.webdriver.chrome.service import Service # Imports Service to manage the ChromeDriver service.
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException # Imports specific exceptions for error handling.
from webdriver_manager.chrome import ChromeDriverManager # Imports ChromeDriverManager to automatically manage ChromeDriver.

from utils.rate_limiter import RateLimiter # Imports a custom RateLimiter utility.


class SeleniumEbayScraper: # Defines the main scraper class.
    """Selenium-based eBay scraper with enhanced anti-detection"""
    
    def __init__(self, config): # Constructor for the scraper class, takes a config object.
        self.config = config # Stores the configuration.
        self.logger = logging.getLogger(__name__) # Initializes a logger for this class.
        self.rate_limiter = RateLimiter(config.request_delay) # Initializes a rate limiter with a delay from the config.
        
        # Initialize WebDriver
        self.driver = None # Initializes the WebDriver instance to None.
        self._setup_driver() # Calls a private method to set up the WebDriver.
        
        # eBay URLs
        self.base_url = "https://www.ebay.com" # Sets the base URL for eBay.
        self.search_url = "https://www.ebay.com/sch/i.html" # Sets the search URL for eBay.
        
    def _setup_driver(self):
        """Setup Chrome WebDriver with anti-detection measures"""
        try:
            chrome_options = webdriver.ChromeOptions()
            
            # Anti-detection measures
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Normal browser behavior
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--start-maximized")
            
            # Add realistic user agent
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Install ChromeDriver automatically
            service = Service(ChromeDriverManager().install())
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute JavaScript in separate calls
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            # Add realistic properties
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            self.logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            # Fall back to headless mode if regular mode fails
            try:
                chrome_options.add_argument("--headless")
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.logger.info("Chrome WebDriver initialized in headless mode")
            except Exception as e2:
                self.logger.error(f"Failed to initialize headless WebDriver: {str(e2)}")
                raise

    def _handle_security_check(self) -> bool:
        """Handle eBay's security check page"""
        try:
            # Wait a bit for the page to load
            time.sleep(3)
            
            page_source = self.driver.page_source.lower()
            
            # Check if we're on a security check page
            if any(indicator in page_source for indicator in ['checking your browser', 'security check', 'please wait']):
                self.logger.info("Security check detected, waiting for resolution...")
                
                # Try to interact with the page to trigger the security check
                try:
                    self.driver.find_element(By.TAG_NAME, 'body').click()
                except:
                    pass
                
                # Wait up to 60 seconds for the page to resolve
                for _ in range(60):
                    time.sleep(1)
                    current_source = self.driver.page_source.lower()
                    
                    if not any(indicator in current_source for indicator in ['checking your browser', 'security check']):
                        self.logger.info("Security check resolved automatically")
                        return True
                
                self.logger.warning("Security check did not resolve automatically")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error handling security check: {str(e)}")
            return False
        
    def _get_page(self, url: str) -> bool:
        """Navigate to a page and handle security checks"""
        if not self.driver:
            return False
            
        self.rate_limiter.wait()
        
        try:
            self.logger.debug(f"Navigating to: {url}")
            # Load eBay home first to set cookies
            self.driver.get("https://www.ebay.com")
            time.sleep(1)  # Let the page load

            # ✅ Set cookies to force USD + English locale
            self.driver.add_cookie({"name": "dp1", "value": "bu1p/QEBfX0BAXw**"})  # forces USD
            self.driver.add_cookie({"name": "nonsession", "value": "USD"})  # just in case
            self.driver.add_cookie({"name": "currency", "value": "USD"})
            self.driver.add_cookie({"name": "site", "value": "0"})

            # Now load the real search page
            self.driver.get(url)

            
            if not self._handle_security_check():
                return False
            
            # Wait for either the search results or product details to load
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: (
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".s-item")) or
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#itemTitle"))
                    )
                )
            except TimeoutException:
                self.logger.warning("Page load timeout, continuing anyway")
            
            self.rate_limiter.on_success()
            return True
            
        except WebDriverException as e:
            self.logger.error(f"WebDriver error accessing {url}: {str(e)}")
            self.rate_limiter.on_failure()
            return False
        
    def scrape_search_results(self, search_query: str, max_pages: int = 1, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape search results for a given query"""
        all_items = []
        product_links = []
        
        try:
            # Construct search URL
            params = {
                '_nkw': search_query,
                '_ipg': 100  # Items per page
            }
            search_url = self.search_url + '?' + '&'.join([f'{k}={v}' for k, v in params.items()])
            
            for page in range(1, max_pages + 1):
                # Update page parameter
                if page > 1:
                    page_url = f"{search_url}&_pgn={page}&LH_BIN=1&_fcid=1&_localstpos=10001&_stpos=10001&_fspt=1"
                else:
                    page_url = search_url
                    
                if not self._get_page(page_url):
                    self.logger.warning(f"Failed to load page {page}")
                    continue
                    
                # Extract product links from current page
                current_links = self._extract_product_links()
                product_links.extend(current_links)
                
                # Log progress
                self.logger.info(f"Page {page}: Found {len(current_links)} product links")
                
                # Break if we've reached max_items
                if max_items and len(product_links) >= max_items:
                    product_links = product_links[:max_items]
                    break
                    
            # Now scrape each product
            for i, product_url in enumerate(product_links):
                if max_items and len(all_items) >= max_items:
                    break
                    
                self.logger.info(f"Scraping product {i+1}/{len(product_links)}: {product_url}")
                product_data = self.scrape_product_details(product_url)
                if product_data:
                    all_items.append(product_data)
                    
        except Exception as e:
            self.logger.error(f"Error during search scraping: {str(e)}")
        finally:
            self._cleanup()
            
        return all_items

    def _extract_product_links(self) -> List[str]: # Defines a private method to extract product links.
        """Extract product URLs from search results"""
        links = [] # Initializes an empty list to store links.
        
        try: # Begins a try block for link extraction.
            # Wait for search results to load
            WebDriverWait(self.driver, 10).until( # Waits up to 10 seconds.
                EC.presence_of_element_located((By.CSS_SELECTOR, ".s-item")) # Waits until an element with class 's-item' is present.
            )
            
            # Find product links using multiple selectors
            link_selectors = [ # Defines a list of CSS selectors to find product links.
                ".s-item__link",
                ".s-item .s-item__title a",
                "a[href*='/itm/']"
            ]
            
            for selector in link_selectors: # Iterates through each link selector.
                try: # Begins a nested try block for finding elements with a specific selector.
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector) # Finds all elements matching the current selector.
                    for element in elements: # Iterates through each found element.
                        try: # Begins a nested try block for getting the href attribute.
                            href = element.get_attribute('href') # Gets the 'href' attribute of the element.
                            if href and '/itm/' in href and 'ebay.com' in href:
                                if '123456' in href:
                                    continue  # Skip placeholder dummy URLs
                                clean_url = self._clean_ebay_url(href)
                                if clean_url not in links:
                                    links.append(clean_url)
                        except Exception: # Catches any exception during href extraction.
                            continue # Continues to the next element if an error occurs.
                except Exception: # Catches any exception during element finding with a specific selector.
                    continue # Continues to the next selector if an error occurs.
            
        except Exception as e: # Catches any exception during the overall link extraction.
            self.logger.error(f"Error extracting product links: {str(e)}") # Logs the error.
        
        return links[:50]  # Limit to 50 links per page # Returns a slice of the links, limiting to 50.
    
    def _clean_ebay_url(self, url: str) -> str: # Defines a private method to clean eBay URLs.
        """Clean eBay URL by removing tracking parameters"""
        match = re.search(r'/itm/(\d+)', url) # Uses regex to find the item ID in the URL.
        if match: # Checks if a match was found.
            item_id = match.group(1) # Extracts the item ID.
            return f"https://www.ebay.com/itm/{item_id}" # Returns a cleaned URL with only the item ID.
        return url # Returns the original URL if no item ID was found.
    
    def scrape_product_details(self, product_url: str) -> Optional[Dict[str, Any]]: # Defines a method to scrape product details.
        """Scrape detailed product information"""
        if not self._get_page(product_url): # Navigates to the product URL and checks for success.
            return None # Returns None if page navigation failed.
        
        try: # Begins a try block for product detail scraping.
            # Wait for product page to load
            time.sleep(2) # Waits for 2 seconds to allow the page to fully load.
            
            product_data = { # Initializes a dictionary to store product data.
                'listing_url': product_url, # Stores the product's listing URL.
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'), # Stores the timestamp of when the data was scraped.
                'primary_image_url': self._extract_image(), # Extracts and stores the primary image URL.
                'title': self._extract_title(), # Extracts and stores the product title.
                'price': self._extract_price(), # Extracts and stores the product price.
                'condition': self._extract_condition(), # Extracts and stores the product condition.
                'quantity_sold': self._extract_quantity_sold(), # Extracts and stores the quantity sold.
                'item_specifics': self._extract_item_specifics(), # Extracts and stores item specifics.
                'description': self._extract_description() # Extracts and stores the product description.
            }
            
            return product_data # Returns the dictionary of product data.
            
        except Exception as e: # Catches any exception during product detail scraping.
            self.logger.error(f"Error scraping product details from {product_url}: {str(e)}") # Logs the error.
            return None # Returns None if an error occurred.
    
    def _extract_image(self) -> Optional[str]: # Defines a private method to extract the primary image URL.
        """Extract primary image URL"""
        try: # Begins a try block for image extraction.
            selectors = [ # Defines a list of CSS selectors for finding the image.
                '#icImg',
                '#image',
                '.img img',
                '.u-photo img',
                'img[id*="image"]'
            ]
            
            for selector in selectors: # Iterates through each image selector.
                try: # Begins a nested try block for finding an element with a specific selector.
                    img_element = self.driver.find_element(By.CSS_SELECTOR, selector) # Finds the image element.
                    src = img_element.get_attribute('src') # Gets the 'src' attribute of the image.
                    if src and 'http' in src and not 'data:' in src: # Checks if src exists, contains 'http', and is not a data URI.
                        return src # Returns the image source URL.
                except NoSuchElementException: # Catches NoSuchElementException if the element is not found.
                    continue # Continues to the next selector if the element is not found.
        except Exception as e: # Catches any general exception during image extraction.
            self.logger.debug(f"Error extracting image: {str(e)}") # Logs the debug error.
        
        return None # Returns None if no image URL was found.
    
    def _extract_title(self) -> Optional[str]: # Defines a private method to extract the product title.
        """Extract product title"""
        try: # Begins a try block for title extraction.
            selectors = [ # Defines a list of CSS selectors for finding the title.
                '#x-title-label-lbl',
                '.x-title-label-lbl',
                'h1[id*="title"]',
                '.it-ttl',
                'h1'
            ]
            
            for selector in selectors: # Iterates through each title selector.
                try: # Begins a nested try block for finding an element with a specific selector.
                    element = self.driver.find_element(By.CSS_SELECTOR, selector) # Finds the title element.
                    title = element.text.strip() # Gets the text of the element and strips whitespace.
                    if title and len(title) > 5 and 'checking your browser' not in title.lower(): # Checks if title is valid and not a security check message.
                        return title # Returns the extracted title.
                except NoSuchElementException: # Catches NoSuchElementException if the element is not found.
                    continue # Continues to the next selector.
        except Exception as e: # Catches any general exception during title extraction.
            self.logger.debug(f"Error extracting title: {str(e)}") # Logs the debug error.
        
        return None # Returns None if no title was found.
    
    def _extract_price(self) -> Optional[str]:
        """Try to extract product price from known selectors."""
        selectors = [
            '#prcIsum',
            '#prcIsum_bidPrice',
            '#mm-saleDscPrc',
            '.x-price-approx__price',
            '.display-price',
            '[itemprop="price"]',
            '.s-item__price',
            '.notranslate',
            '.item-price',
            '.s-item__detail .s-item__price',
            '.x-price-approx__value'
        ]

        for selector in selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                price_text = element.text.strip()
                if price_text and any(sym in price_text for sym in ['$', '€', '£', '₹']):
                    return price_text
            except Exception:
                continue  # Move to next selector if not found or error

        self.logger.warning("❌ Price not found with any known selector.")
        return None

    def _extract_condition(self) -> Optional[str]: # Defines a private method to extract the product condition.
        """Extract condition"""
        try: # Begins a try block for condition extraction.
            # Look in page text for condition information
            page_text = self.driver.page_source.lower() # Gets the page source and converts it to lowercase.
            condition_patterns = [ # Defines a list of regex patterns to find condition information.
                r'condition[^:]*:?\s*(new|used|refurbished|open box|for parts|pre-owned)',
                r'item condition[^:]*:?\s*(new|used|refubished|open box|for parts|pre-owned)'
            ]
            
            for pattern in condition_patterns: # Iterates through each condition regex pattern.
                match = re.search(pattern, page_text, re.IGNORECASE) # Searches for the pattern in the page text (case-insensitive).
                if match: # Checks if a match was found.
                    return match.group(1).title() # Returns the captured group (the condition), title-cased.
                    
        except Exception as e: # Catches any general exception during condition extraction.
            self.logger.debug(f"Error extracting condition: {str(e)}") # Logs the debug error.
        
        return None # Returns None if no condition was found.
    
    def _extract_quantity_sold(self) -> Optional[int]: # Defines a private method to extract the quantity sold.
        """Extract quantity sold"""
        try: # Begins a try block for quantity sold extraction.
            page_text = self.driver.page_source # Gets the page source.
            sold_patterns = [ # Defines a list of regex patterns to find quantity sold.
                r'(\d+[\d,]*)\s*sold',
                r'sold:\s*(\d+[\d,]*)',
                r'(\d+[\d,]*)\s*vendus?',
                r'quantity\s*sold:\s*(\d+[\d,]*)'
            ]
            
            for pattern in sold_patterns: # Iterates through each sold quantity regex pattern.
                matches = re.findall(pattern, page_text, re.IGNORECASE) # Finds all matches for the pattern.
                if matches: # Checks if any matches were found.
                    try: # Begins a nested try block for converting matches to integers.
                        quantities = [int(match.replace(',', '')) for match in matches] # Converts matched strings to integers, removing commas.
                        return max(quantities) # Returns the maximum quantity found.
                    except ValueError: # Catches ValueError if conversion to int fails.
                        continue # Continues to the next pattern if conversion fails.
        except Exception as e: # Catches any general exception during quantity sold extraction.
            self.logger.debug(f"Error extracting quantity sold: {str(e)}") # Logs the debug error.
        
        return None # Returns None if no quantity sold was found.
    
    def _extract_item_specifics(self) -> Dict[str, str]: # Defines a private method to extract item specifics.
        """Extract item specifics"""
        specifics = {} # Initializes an empty dictionary to store specifics.
        
        try: # Begins a try block for item specifics extraction.
            # Try to find item specifics table or section
            selectors = [ # Defines a list of CSS selectors for finding item specifics.
                '.itemAttr tr',
                '.item-specifics tr',
                '[data-testid="item-specifics"] tr'
            ]
            
            for selector in selectors: # Iterates through each item specifics selector.
                try: # Begins a nested try block for finding elements with a specific selector.
                    rows = self.driver.find_elements(By.CSS_SELECTOR, selector) # Finds all table rows matching the selector.
                    for row in rows: # Iterates through each row.
                        try: # Begins a nested try block for extracting key-value pairs from cells.
                            cells = row.find_elements(By.TAG_NAME, 'td') # Finds all 'td' (table data) cells within the row.
                            if len(cells) >= 2: # Checks if there are at least two cells (key and value).
                                key = cells[0].text.strip().rstrip(':') # Extracts the key from the first cell, strips whitespace, and removes trailing colon.
                                value = cells[1].text.strip() # Extracts the value from the second cell and strips whitespace.
                                if key and value and len(key) < 50 and len(value) < 200: # Validates key and value length.
                                    specifics[key] = value # Stores the key-value pair in the dictionary.
                        except Exception: # Catches any exception during cell processing.
                            continue # Continues to the next row if an error occurs.
                except Exception: # Catches any exception during finding rows with a specific selector.
                    continue # Continues to the next selector.
                    
        except Exception as e: # Catches any general exception during item specifics extraction.
            self.logger.debug(f"Error extracting item specifics: {str(e)}") # Logs the debug error.
        
        return specifics # Returns the dictionary of item specifics.
    
    def _extract_description(self) -> Optional[str]: # Defines a private method to extract the product description.
        """Extract description"""
        try: # Begins a try block for description extraction.
            selectors = [ # Defines a list of CSS selectors for finding the description.
                '#desc_div',
                '.item-description',
                '[data-testid="description"]',
                '.description'
            ]
            
            for selector in selectors: # Iterates through each description selector.
                try: # Begins a nested try block for finding an element with a specific selector.
                    element = self.driver.find_element(By.CSS_SELECTOR, selector) # Finds the description element.
                    description = element.text.strip() # Gets the text of the element and strips whitespace.
                    if description and len(description) > 20: # Checks if the description is valid and reasonably long.
                        return description[:5000]  # Limit length # Returns the description, truncated to 5000 characters.
                except NoSuchElementException: # Catches NoSuchElementException if the element is not found.
                    continue # Continues to the next selector.
        except Exception as e: # Catches any general exception during description extraction.
            self.logger.debug(f"Error extracting description: {str(e)}") # Logs the debug error.
        
        return None # Returns None if no description was found.
    
    def _cleanup(self): # Defines a private method for resource cleanup.
        """Clean up resources"""
        if self.driver: # Checks if the driver instance exists.
            try: # Begins a try block for quitting the driver.
                self.driver.quit() # Quits the WebDriver, closing the browser.
                self.logger.info("WebDriver closed successfully") # Logs a success message.
            except Exception as e: # Catches any exception during driver quitting.
                self.logger.error(f"Error closing WebDriver: {str(e)}") # Logs the error.
    
    def __del__(self): # Defines the destructor method for the class.
        """Destructor to ensure cleanup"""
        self._cleanup() # Calls the cleanup method when the object is about to be destroyed.