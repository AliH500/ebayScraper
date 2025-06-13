"""
Enhanced eBay Scraper Module with CAPTCHA Handling
Uses Selenium WebDriver for better browser simulation and CAPTCHA handling.
"""

import logging # Imports the logging module for logging events.
import time # Imports the time module for time-related functions like delays.
import re # Imports the regular expression module for pattern matching.
from typing import Dict, List, Optional, Any # Imports type hints for better code readability and maintainability.
from urllib.parse import urljoin # Imports urljoin for constructing absolute URLs.

from selenium import webdriver # Imports the selenium webdriver for browser automation.
from selenium.webdriver.common.by import By # Imports By class for locating elements using various strategies.
from selenium.webdriver.support.ui import WebDriverWait # Imports WebDriverWait for explicit waits.
from selenium.webdriver.support import expected_conditions as EC # Imports expected_conditions for common conditions to wait for.
from selenium.webdriver.chrome.options import Options # Imports Options class to customize Chrome browser settings.
from selenium.webdriver.chrome.service import Service # Imports Service class to manage the ChromeDriver service.
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException # Imports specific Selenium exceptions.
from webdriver_manager.chrome import ChromeDriverManager # Imports ChromeDriverManager to automatically manage ChromeDriver.

from utils.rate_limiter import RateLimiter # Imports RateLimiter utility for controlling request frequency.


class EnhancedEbayScraper:
    """Enhanced eBay scraper with Selenium and CAPTCHA handling"""
    
    def __init__(self, config):
        """Initializes the EnhancedEbayScraper with configuration."""
        self.config = config # Stores the configuration object.
        self.logger = logging.getLogger(__name__) # Gets a logger instance for this module.
        self.rate_limiter = RateLimiter(config.request_delay) # Initializes a RateLimiter with the configured delay.
        
        # Initialize WebDriver
        self.driver = None # Initializes the WebDriver instance to None.
        self._setup_driver() # Calls the private method to set up the WebDriver.
        
        # eBay URLs
        self.base_url = "https://www.ebay.com" # Defines the base URL for eBay.
        self.search_url = "https://www.ebay.com/sch/i.html" # Defines the search URL for eBay.
        
    def _setup_driver(self):
        """Setup Chrome WebDriver with appropriate options"""
        try:
            chrome_options = Options() # Creates an instance of ChromeOptions.
            
            # Add options to appear more human-like
            chrome_options.add_argument("--disable-blink-features=AutomationControlled") # Disables the AutomationControlled feature to avoid detection.
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) # Excludes the "enable-automation" switch.
            chrome_options.add_experimental_option('useAutomationExtension', False) # Disables the use of automation extension.
            
            # Window size and user agent
            chrome_options.add_argument("--window-size=1920,1080") # Sets the browser window size.
            chrome_options.add_argument("--disable-web-security") # Disables web security.
            chrome_options.add_argument("--disable-features=VizDisplayCompositor") # Disables VizDisplayCompositor feature.
            
            # Disable images for faster loading (optional)
            prefs = {
                "profile.managed_default_content_settings.images": 2, # Sets a preference to disable image loading.
                "profile.default_content_setting_values.notifications": 2 # Sets a preference to disable notifications.
            }
            chrome_options.add_experimental_option("prefs", prefs) # Adds the experimental preferences to Chrome options.
            
            # Install ChromeDriver automatically
            service = Service(ChromeDriverManager().install()) # Installs and sets up the ChromeDriver service automatically.
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options) # Initializes the Chrome WebDriver with the specified service and options.
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})") # Executes a JavaScript snippet to hide WebDriver detection.
            
            self.logger.info("Chrome WebDriver initialized successfully") # Logs a success message.
            
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}") # Logs an error if WebDriver initialization fails.
            raise # Re-raises the exception.
    
    def _wait_for_captcha_or_content(self, timeout: int = 30) -> bool:
        """Wait for either CAPTCHA resolution or page content to load"""
        if not self.driver: # Checks if the driver is not initialized.
            return False # Returns False if the driver is not available.
            
        try:
            # Check for CAPTCHA indicators
            captcha_selectors = [
                "iframe[src*='captcha']", # CSS selector for an iframe containing 'captcha'.
                "[id*='captcha']", # CSS selector for an element with an ID containing 'captcha'.
                "[class*='captcha']", # CSS selector for an element with a class containing 'captcha'.
                "form[action*='captcha']" # CSS selector for a form with an action containing 'captcha'.
            ]
            
            # Check for normal content indicators
            content_selectors = [
                ".s-item", # CSS selector for a search result item.
                ".x-title-label-lbl", # CSS selector for a title label.
                "#mainContent" # CSS selector for the main content area.
            ]
            
            wait = WebDriverWait(self.driver, timeout) # Creates a WebDriverWait instance.
            
            # Wait for either CAPTCHA or content to appear
            for i in range(timeout): # Loops for the specified timeout duration.
                # Check for CAPTCHA
                for selector in captcha_selectors: # Iterates through CAPTCHA selectors.
                    try:
                        captcha_element = self.driver.find_element(By.CSS_SELECTOR, selector) # Tries to find a CAPTCHA element.
                        if captcha_element.is_displayed(): # Checks if the CAPTCHA element is displayed.
                            self.logger.warning("CAPTCHA detected. Please solve it manually.") # Logs a warning about CAPTCHA.
                            self._handle_captcha_interaction() # Calls the method to handle CAPTCHA interaction.
                            return True # Returns True indicating CAPTCHA was handled.
                    except NoSuchElementException: # Catches if the element is not found.
                        pass # Continues to the next selector.
                
                # Check for normal content
                for selector in content_selectors: # Iterates through content selectors.
                    try:
                        content_element = self.driver.find_element(By.CSS_SELECTOR, selector) # Tries to find a content element.
                        if content_element.is_displayed(): # Checks if the content element is displayed.
                            self.logger.info("Page content loaded successfully") # Logs that page content loaded.
                            return True # Returns True indicating content loaded.
                    except NoSuchElementException: # Catches if the element is not found.
                        pass # Continues to the next selector.
                
                time.sleep(1) # Waits for 1 second before checking again.
            
            return False # Returns False if neither CAPTCHA nor content was found within the timeout.
            
        except Exception as e:
            self.logger.error(f"Error waiting for content: {str(e)}") # Logs an error if an exception occurs.
            return False # Returns False due to an error.
    
    def _handle_captcha_interaction(self):
        """Handle CAPTCHA interaction - wait for user to solve it"""
        self.logger.info("CAPTCHA detected. Waiting for manual resolution...") # Logs that CAPTCHA was detected and awaiting manual resolution.
        
        # Wait up to 5 minutes for user to solve CAPTCHA
        max_wait_time = 300  # 5 minutes in seconds.
        start_time = time.time() # Records the start time for the wait.
        
        while time.time() - start_time < max_wait_time: # Loops until the max wait time is exceeded.
            try:
                # Check if we're still on a CAPTCHA page
                page_source = self.driver.page_source.lower() # Gets the current page source and converts it to lowercase.
                if 'captcha' not in page_source and 'security check' not in page_source: # Checks if CAPTCHA or security check keywords are no longer in the page source.
                    self.logger.info("CAPTCHA appears to be resolved") # Logs that CAPTCHA appears resolved.
                    time.sleep(2) # Waits for 2 seconds to ensure the page fully loads after resolution.
                    return True # Returns True indicating CAPTCHA was resolved.
                
                time.sleep(5) # Checks every 5 seconds.
                
            except Exception as e:
                self.logger.error(f"Error checking CAPTCHA status: {str(e)}") # Logs an error if checking CAPTCHA status fails.
                break # Breaks out of the loop on error.
        
        self.logger.warning("CAPTCHA resolution timeout") # Logs a warning if CAPTCHA resolution times out.
        return False # Returns False if CAPTCHA was not resolved within the timeout.
    
    def _get_page(self, url: str) -> bool:
        """Navigate to a page and handle potential CAPTCHAs"""
        self.rate_limiter.wait() # Waits according to the rate limit.
        
        try:
            self.logger.debug(f"Navigating to: {url}") # Logs the URL being navigated to.
            self.driver.get(url) # Navigates the browser to the specified URL.
            
            # Wait for page to load and handle CAPTCHA if needed
            success = self._wait_for_captcha_or_content() # Calls the method to wait for content or CAPTCHA.
            
            if success: # Checks if the page loaded successfully or CAPTCHA was handled.
                self.rate_limiter.on_success() # Notifies the rate limiter of a successful request.
                return True # Returns True indicating successful page load.
            else:
                self.rate_limiter.on_failure() # Notifies the rate limiter of a failed request.
                return False # Returns False indicating page load failure.
                
        except WebDriverException as e:
            self.logger.error(f"WebDriver error accessing {url}: {str(e)}") # Logs a WebDriver error.
            self.rate_limiter.on_failure() # Notifies the rate limiter of a failed request.
            return False # Returns False due to WebDriver error.
    
    def scrape_search_results(self, search_query: str, max_pages: int = 1, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape eBay search results with enhanced handling"""
        all_items = [] # Initializes an empty list to store all scraped items.
        
        try:
            for page in range(1, max_pages + 1): # Loops through the specified number of pages.
                self.logger.info(f"Scraping page {page} of search results...") # Logs the current page being scraped.
                
                # Build search URL
                search_url = f"{self.search_url}?_nkw={search_query.replace(' ', '+')}&_pgn={page}" # Constructs the search URL with query and page number.
                
                if not self._get_page(search_url): # Tries to navigate to the search page.
                    self.logger.warning(f"Failed to load search page {page}") # Logs a warning if the page fails to load.
                    continue # Continues to the next page if loading fails.
                
                # Extract product links
                product_links = self._extract_product_links_selenium() # Extracts product links from the current search results page.
                
                if not product_links: # Checks if no product links were found.
                    self.logger.warning(f"No product links found on page {page}") # Logs a warning if no links are found.
                    break # Breaks the loop if no product links are found on the current page.
                
                self.logger.info(f"Found {len(product_links)} products on page {page}") # Logs the number of products found.
                
                # Scrape each product
                for product_url in product_links: # Iterates through each extracted product URL.
                    if max_items and len(all_items) >= max_items: # Checks if the maximum items limit has been reached.
                        self.logger.info(f"Reached maximum items limit: {max_items}") # Logs that the maximum items limit has been reached.
                        return all_items # Returns all scraped items.
                    
                    self.logger.info(f"Scraping product {len(all_items) + 1}: {product_url}") # Logs the current product being scraped.
                    
                    product_data = self.scrape_product_details(product_url) # Scrapes detailed information for the product.
                    if product_data: # Checks if product data was successfully scraped.
                        all_items.append(product_data) # Appends the scraped product data to the list.
                        self.logger.debug(f"Successfully scraped: {product_data.get('title', 'Unknown')}") # Logs the title of the successfully scraped product.
                    else:
                        self.logger.warning(f"Failed to scrape product: {product_url}") # Logs a warning if product scraping fails.
            
            return all_items # Returns the list of all scraped items.
            
        finally:
            self._cleanup() # Ensures cleanup (closing the WebDriver) happens after the scraping process.
    
    def _extract_product_links_selenium(self) -> List[str]:
        """Extract product URLs using Selenium"""
        links = [] # Initializes an empty list to store extracted links.
        
        try:
            # Wait for search results to load
            wait = WebDriverWait(self.driver, 10) # Creates a WebDriverWait instance with a 10-second timeout.
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".s-item"))) # Waits until an element with class "s-item" is present.
            
            # Find product links
            link_elements = self.driver.find_elements(By.CSS_SELECTOR, ".s-item__link") # Finds all elements with class "s-item__link".
            
            for element in link_elements: # Iterates through each link element.
                try:
                    href = element.get_attribute('href') # Gets the 'href' attribute of the element.
                    if href and '/itm/' in href: # Checks if 'href' exists and contains '/itm/'.
                        # Clean the URL
                        clean_url = self._clean_ebay_url(href) # Cleans the extracted URL.
                        if clean_url not in links: # Checks if the cleaned URL is not already in the list.
                            links.append(clean_url) # Adds the cleaned URL to the list.
                except Exception as e:
                    self.logger.debug(f"Error extracting link: {str(e)}") # Logs a debug message for link extraction errors.
                    continue # Continues to the next element.
            
        except Exception as e:
            self.logger.error(f"Error extracting product links: {str(e)}") # Logs an error if product link extraction fails.
        
        return links # Returns the list of extracted product links.
    
    def _clean_ebay_url(self, url: str) -> str:
        """Clean eBay URL by removing tracking parameters"""
        match = re.search(r'/itm/(\d+)', url) # Searches for the item ID pattern in the URL.
        if match: # Checks if a match is found.
            item_id = match.group(1) # Extracts the item ID.
            return f"https://www.ebay.com/itm/{item_id}" # Returns a cleaned eBay item URL.
        return url # Returns the original URL if no item ID pattern is found.
    
    def scrape_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed product information using Selenium"""
        if not self._get_page(product_url): # Attempts to navigate to the product URL.
            return None # Returns None if the page cannot be loaded.
        
        try:
            product_data = {
                'listing_url': product_url, # Stores the product's listing URL.
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'), # Records the timestamp of when the data was scraped.
                'primary_image_url': self._extract_image_selenium(), # Extracts the primary image URL.
                'title': self._extract_title_selenium(), # Extracts the product title.
                'price': self._extract_price_selenium(), # Extracts the product price.
                'condition': self._extract_condition_selenium(), # Extracts the product condition.
                'quantity_sold': self._extract_quantity_sold_selenium(), # Extracts the quantity sold.
                'item_specifics': self._extract_item_specifics_selenium(), # Extracts item specifics.
                'description': self._extract_description_selenium() # Extracts the product description.
            }
            
            return product_data # Returns the dictionary containing product data.
            
        except Exception as e:
            self.logger.error(f"Error scraping product details from {product_url}: {str(e)}") # Logs an error if product details scraping fails.
            return None # Returns None due to an error.
    
    def _extract_image_selenium(self) -> Optional[str]:
        """Extract primary image URL using Selenium"""
        try:
            selectors = ['#icImg', '#image', '.img img', '.u-photo img'] # Defines CSS selectors to try for image extraction.
            
            for selector in selectors: # Iterates through each selector.
                try:
                    img_element = self.driver.find_element(By.CSS_SELECTOR, selector) # Tries to find the image element using the current selector.
                    src = img_element.get_attribute('src') # Gets the 'src' attribute of the image element.
                    if src and 'http' in src: # Checks if 'src' exists and contains 'http'.
                        return src # Returns the image source URL.
                except NoSuchElementException: # Catches if the element is not found.
                    continue # Continues to the next selector.
        except Exception as e:
            self.logger.debug(f"Error extracting image: {str(e)}") # Logs a debug message for image extraction errors.
        
        return None # Returns None if no image URL is found.
    
    def _extract_title_selenium(self) -> Optional[str]:
        """Extract product title using Selenium"""
        try:
            selectors = ['#x-title-label-lbl', '.x-title-label-lbl', 'h1[id*="title"]'] # Defines CSS selectors to try for title extraction.
            
            for selector in selectors: # Iterates through each selector.
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector) # Tries to find the title element using the current selector.
                    title = element.text.strip() # Gets the text of the element and strips whitespace.
                    if title and len(title) > 5: # Checks if the title exists and is longer than 5 characters.
                        return title # Returns the extracted title.
                except NoSuchElementException: # Catches if the element is not found.
                    continue # Continues to the next selector.
        except Exception as e:
            self.logger.debug(f"Error extracting title: {str(e)}") # Logs a debug message for title extraction errors.
        
        return None # Returns None if no title is found.
    
    def _extract_price_selenium(self) -> Optional[str]:
        """Extract price using Selenium"""
        try:
            selectors = [
                '.price .notranslate', # CSS selector for a price element.
                '[data-testid="price"] .notranslate', # CSS selector for a price element with data-testid.
                '.display-price', # CSS selector for a display price.
                '.bin-price .notranslate' # CSS selector for a buy-it-now price.
            ]
            
            for selector in selectors: # Iterates through each selector.
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector) # Tries to find the price element using the current selector.
                    price_text = element.text.strip() # Gets the text of the element and strips whitespace.
                    if price_text and '$' in price_text: # Checks if the price text exists and contains '$'.
                        return price_text # Returns the extracted price text.
                except NoSuchElementException: # Catches if the element is not found.
                    continue # Continues to the next selector.
        except Exception as e:
            self.logger.debug(f"Error extracting price: {str(e)}") # Logs a debug message for price extraction errors.
        
        return None # Returns None if no price is found.
    
    def _extract_condition_selenium(self) -> Optional[str]:
        """Extract condition using Selenium"""
        try:
            # Look in item specifics or condition section
            page_text = self.driver.page_source.lower() # Gets the full page source and converts to lowercase.
            condition_match = re.search(r'condition[^:]*:?\s*(new|used|refurbished|open box|for parts)', page_text, re.IGNORECASE) # Searches for condition keywords in the page text.
            if condition_match: # Checks if a condition is matched.
                return condition_match.group(1).title() # Returns the found condition with proper capitalization.
        except Exception as e:
            self.logger.debug(f"Error extracting condition: {str(e)}") # Logs a debug message for condition extraction errors.
        
        return None # Returns None if no condition is found.
    
    def _extract_quantity_sold_selenium(self) -> Optional[int]:
        """Extract quantity sold using Selenium"""
        try:
            page_text = self.driver.page_source # Gets the full page source.
            sold_patterns = [
                r'(\d+[\d,]*)\s*sold', # Regex pattern for "X sold".
                r'sold:\s*(\d+[\d,]*)', # Regex pattern for "sold: X".
                r'(\d+[\d,]*)\s*vendus?' # Regex pattern for French "X vendus".
            ]
            
            for pattern in sold_patterns: # Iterates through each sold quantity pattern.
                matches = re.findall(pattern, page_text, re.IGNORECASE) # Finds all occurrences of the pattern.
                if matches: # Checks if any matches are found.
                    try:
                        quantities = [int(match.replace(',', '')) for match in matches] # Converts matched strings to integers, removing commas.
                        return max(quantities) # Returns the maximum quantity found.
                    except ValueError: # Catches if conversion to int fails.
                        continue # Continues to the next pattern.
        except Exception as e:
            self.logger.debug(f"Error extracting quantity sold: {str(e)}") # Logs a debug message for quantity sold extraction errors.
        
        return None # Returns None if no quantity sold is found.
    
    def _extract_item_specifics_selenium(self) -> Dict[str, str]:
        """Extract item specifics using Selenium"""
        specifics = {} # Initializes an empty dictionary for item specifics.
        
        try:
            # Try to find item specifics table
            rows = self.driver.find_elements(By.CSS_SELECTOR, '.itemAttr tr, .item-specifics tr') # Finds rows within item specifics tables.
            
            for row in rows: # Iterates through each row.
                try:
                    cells = row.find_elements(By.TAG_NAME, 'td') # Finds table data cells within the row.
                    if len(cells) >= 2: # Checks if there are at least two cells (key and value).
                        key = cells[0].text.strip().rstrip(':') # Extracts the key text, strips whitespace, and removes trailing colon.
                        value = cells[1].text.strip() # Extracts the value text and strips whitespace.
                        if key and value: # Checks if both key and value are present.
                            specifics[key] = value # Adds the key-value pair to the specifics dictionary.
                except Exception: # Catches any exception during cell processing.
                    continue # Continues to the next row.
                    
        except Exception as e:
            self.logger.debug(f"Error extracting item specifics: {str(e)}") # Logs a debug message for item specifics extraction errors.
        
        return specifics # Returns the dictionary of item specifics.
    
    def _extract_description_selenium(self) -> Optional[str]:
        """Extract description using Selenium"""
        try:
            selectors = ['#desc_div', '.item-description', '[data-testid="description"]'] # Defines CSS selectors to try for description extraction.
            
            for selector in selectors: # Iterates through each selector.
                try:
                    element = self.driver.find_element(By.CSS_SELECTOR, selector) # Tries to find the description element.
                    description = element.text.strip() # Gets the text of the element and strips whitespace.
                    if description and len(description) > 20: # Checks if the description exists and is longer than 20 characters.
                        return description[:5000] # Returns the first 5000 characters of the description.
                except NoSuchElementException: # Catches if the element is not found.
                    continue # Continues to the next selector.
        except Exception as e:
            self.logger.debug(f"Error extracting description: {str(e)}") # Logs a debug message for description extraction errors.
        
        return None # Returns None if no description is found.
    
    def _cleanup(self):
        """Clean up resources"""
        if self.driver: # Checks if the WebDriver instance exists.
            try:
                self.driver.quit() # Quits the WebDriver, closing the browser.
                self.logger.info("WebDriver closed successfully") # Logs that the WebDriver was closed successfully.
            except Exception as e:
                self.logger.error(f"Error closing WebDriver: {str(e)}") # Logs an error if closing the WebDriver fails.
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        self._cleanup() # Calls the cleanup method when the object is about to be destroyed.