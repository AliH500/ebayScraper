"""
eBay Scraper Module
Handles the core scraping functionality for eBay product listings.
"""
import random
import logging
import re
import time
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse, parse_qs
import json

import requests
from bs4 import BeautifulSoup

from utils.rate_limiter import RateLimiter
from utils.user_agents import UserAgentRotator


class EbayScraper:
    """Main eBay scraping class"""
    
    def __init__(self, config):
        # Initialize scraper with configuration
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        
        # Setup rate limiting and user agent rotation
        self.rate_limiter = RateLimiter(config.request_delay)
        self.user_agent_rotator = UserAgentRotator()
        
        # Configure the HTTP session
        self._setup_session()
        
        # Define eBay URLs
        self.base_url = "https://www.ebay.com"
        self.search_url = "https://www.ebay.com/sch/i.html"
        
    def _setup_session(self):
        """Configure the requests session"""
        # Set up proxy if configured
        if self.config.proxy_url:
            self.session.proxies = {
                'http': self.config.proxy_url,
                'https': self.config.proxy_url
            }
        
        # Set default headers for all requests
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive'
        })
    
    def _get_page(self, url: str, retries: int = 3) -> Optional[BeautifulSoup]:
        """Fetch a page with enhanced error handling"""
        self.rate_limiter.wait()
        
        for attempt in range(retries):
            try:
                # Rotate user agent
                self.session.headers.update({
                    'User-Agent': self.user_agent_rotator.get_random_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': 'https://www.ebay.com/',
                    'DNT': '1',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Sec-Fetch-User': '?1'
                })
                
                self.logger.debug(f"Fetching URL (attempt {attempt + 1}): {url}")
                response = self.session.get(url, timeout=30, allow_redirects=False)
                
                # Handle redirects manually
                if response.status_code in (301, 302, 303, 307, 308):
                    redirect_url = response.headers.get('Location')
                    self.logger.warning(f"Redirect detected from {url} to {redirect_url}")
                    if redirect_url and '/signin/' in redirect_url:
                        self.logger.error("Redirected to sign-in page - possible blocking")
                        return None
                    # Follow the redirect manually with new request
                    response = self.session.get(redirect_url, timeout=30)
                    
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                if self._is_blocked_page(soup):
                    self.logger.warning("Blocked/CAPTCHA detected, increasing delay...")
                    time.sleep(self.config.blocked_delay * (attempt + 1))
                    continue
                    
                if self._is_empty_product_page(soup):
                    self.logger.warning("Empty product page detected")
                    return None
                    
                return soup
                
            except requests.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {str(e)}")
                if attempt < retries - 1:
                    wait_time = 2 ** attempt + random.uniform(0, 1)
                    self.logger.debug(f"Waiting {wait_time:.1f}s before retry...")
                    time.sleep(wait_time)
        
        self.logger.error(f"Failed after {retries} attempts: {url}")
        return None
    
    def _is_blocked_page(self, soup: BeautifulSoup) -> bool:
        """Check if the page indicates we're blocked or facing a CAPTCHA"""
        blocked_indicators = [
            'captcha', 'security check', 'blocked', 'access denied', 'robot',
            'sign in to check out', 'verify your identity', 'sorry we couldn\'t find that page'
        ]
        
        # Check page title
        title = soup.title.string.lower() if soup.title else ""
        if any(indicator in title for indicator in blocked_indicators):
            return True
        
        # Check common CAPTCHA elements
        captcha_selectors = [
            '#captcha-box', '#captcha-container', '#recaptcha',
            'form#captcha-form', 'div.captcha'
        ]
        if any(soup.select(selector) for selector in captcha_selectors):
            return True
        
        # Check HTTP error messages
        error_selectors = [
            '#errorMessage', '.error-container', '.http-error'
        ]
        if any(soup.select(selector) for selector in error_selectors):
            return True
        
        return False
    
    def scrape_search_results(self, search_query: str, max_pages: int = 1, max_items: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scrape eBay search results with improved progress tracking"""
        all_items = []
        items_scraped = 0
        
        # Paginate through search results
        for page in range(1, max_pages + 1):
            self.logger.info(f"Scraping page {page} of search results...")
            
            # Build search URL with parameters
            params = {
                '_nkw': search_query.replace(' ', '+'),  # Space to + for URL encoding
                '_pgn': page,
                '_skc': 0,
                'rt': 'nc'
            }
            
            # Properly encode the URL
            from urllib.parse import urlencode
            search_url = self.search_url + '?' + urlencode(params)
            
            # Fetch search page
            soup = self._get_page(search_url)
            if not soup:
                self.logger.warning(f"Failed to fetch search page {page}")
                continue
                
            # Extract product links
            product_links = self._extract_product_links(soup)
            if not product_links:
                self.logger.warning(f"No product links found on page {page}")
                continue
                
            # Scrape each product
            for link in product_links:
                if max_items and items_scraped >= max_items:
                    break
                    
                product_data = self.scrape_product_details(link)
                if product_data:
                    all_items.append(product_data)
                    items_scraped += 1
                    
            # Delay between pages
            time.sleep(self.config.request_delay)
            
        return all_items    
    def _extract_product_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract product URLs from search results page with better validation"""
        links = set()  # Using set to avoid duplicates
        
        # More comprehensive selectors
        selectors = [
            'a[href*="/itm/"]:not([href*="mailto"])',  # eBay item links
            '.s-item__wrapper a.s-item__link',  # Modern eBay layout
            '.srp-results .s-item a',  # Another modern layout
            '.lvtitle a',  # List view items
            '.vip'  # Old style items
        ]
        
        for selector in selectors:
            for element in soup.select(selector):
                href = element.get('href', '')
                if href and '/itm/' in href:
                    # Normalize URL
                    if href.startswith('//'):
                        href = 'https:' + href
                    elif href.startswith('/'):
                        href = self.base_url + href
                    
                    # Clean and validate URL
                    clean_url = self._clean_ebay_url(href)
                    if clean_url and self._validate_ebay_url(clean_url):
                        links.add(clean_url)
        
        return list(links)
    
    def _clean_ebay_url(self, url: str) -> str:
        """Clean eBay URL by removing tracking parameters"""
        # Extract just the item ID and create clean URL
        match = re.search(r'/itm/(\d+)', url)
        if match:
            item_id = match.group(1)
            return f"https://www.ebay.com/itm/{item_id}"
        return url
    
    def scrape_product_details(self, product_url: str) -> Optional[Dict[str, Any]]:
        """Scrape detailed information from a product page with better error handling"""
        if not self._validate_ebay_url(product_url):
            self.logger.error(f"Invalid eBay URL: {product_url}")
            return None
        
        soup = self._get_page(product_url)
        if not soup:
            return None
        
        try:
            # Check if product page is valid
            if self._is_empty_product_page(soup):
                self.logger.warning(f"Empty product page: {product_url}")
                return None
            
            product_data = {
                'listing_url': product_url,
                'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'primary_image_url': self._extract_primary_image(soup),
                'title': self._extract_title(soup),
                'price': self._extract_price(soup),
                'condition': self._extract_condition(soup),
                'quantity_sold': self._extract_quantity_sold(soup),
                'seller_info': self._extract_seller_info(soup),
                'item_specifics': self._extract_item_specifics(soup),
                'description': self._extract_description(soup),
                'shipping_info': self._extract_shipping_info(soup)
            }
            
            # Validate we got at least some core data
            if not product_data.get('title') or not product_data.get('price'):
                self.logger.warning(f"Incomplete product data from: {product_url}")
                return None
                
            return product_data
            
        except Exception as e:
            self.logger.error(f"Error scraping {product_url}: {str(e)}", exc_info=True)
            return None
    
    def _extract_primary_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract primary product image URL"""
        # Multiple selectors to handle different image layouts
        selectors = [
            '#icImg',
            '#image',
            '.img img',
            '.u-photo img',
            '[data-zoom-src]',
            '.img640 img'
        ]
        
        # Try each selector until we find an image
        for selector in selectors:
            img = soup.select_one(selector)
            if img:
                src = img.get('src') or img.get('data-zoom-src') or img.get('data-src')
                if src:
                    # Normalize image URL
                    if src.startswith('//'):
                        src = 'https:' + src
                    return src
        
        return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product title"""
        selectors = [
            '#x-title-label-lbl',
            '.x-title-label-lbl',
            'h1[id*="title"]',
            '.it-ttl',
            'h1'
        ]
        
        # Try each title selector
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text(strip=True)
                # Basic validation to ensure we got a real title
                if title and len(title) > 5:
                    return title
        
        return None
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product price"""
        selectors = [
            '.price .notranslate',
            '[data-testid="price"] .notranslate',
            '.u-price .notranslate',
            '.display-price',
            '.bin-price .notranslate',
            '.auction-price .notranslate'
        ]
        
        # Try each price selector
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                # Extract just the numeric price value
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    return price_text
        
        return None
    
    def _extract_condition(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract item condition"""
        # Keywords that might indicate condition
        condition_keywords = ['condition', 'état']
        
        # First check item specifics section
        specifics = soup.select('.itemAttr')
        for specific in specifics:
            text = specific.get_text().lower()
            if any(keyword in text for keyword in condition_keywords):
                # Extract condition from text
                condition_match = re.search(r'(new|used|refurbished|open box|for parts)', text, re.IGNORECASE)
                if condition_match:
                    return condition_match.group(1).title()
        
        # Fallback to direct condition selectors
        selectors = [
            '[data-testid="condition"]',
            '.condition-text',
            '.item-condition'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None
    
    def _extract_quantity_sold(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract quantity sold (very important field)"""
        # Patterns that might indicate sold quantity
        sold_patterns = [
            r'(\d+[\d,]*)\s*sold',
            r'sold:\s*(\d+[\d,]*)',
            r'(\d+[\d,]*)\s*vendus?',
            r'quantity\s*sold:\s*(\d+[\d,]*)'
        ]
        
        # Search page text for quantity sold patterns
        page_text = soup.get_text()
        
        for pattern in sold_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            if matches:
                try:
                    # Get highest quantity found (in case of multiple matches)
                    quantities = [int(match.replace(',', '')) for match in matches]
                    return max(quantities)
                except ValueError:
                    continue
        
        # Check specific elements that might contain sold quantity
        selectors = [
            '[data-testid="sold-quantity"]',
            '.sold-quantity',
            '.quantity-sold'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text()
                numbers = re.findall(r'\d+', text.replace(',', ''))
                if numbers:
                    try:
                        return int(numbers[0])
                    except ValueError:
                        continue
        
        return None
    
    def _extract_item_specifics(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract item specifics (key-value pairs)"""
        specifics = {}
        
        # Selectors for different item specifics layouts
        selectors = [
            '.itemAttr',
            '.item-specifics tr',
            '[data-testid="item-specifics"] tr'
        ]
        
        # Extract key-value pairs from tables
        for selector in selectors:
            rows = soup.select(selector)
            for row in rows:
                cells = row.find_all(['td', 'th', 'div'])
                if len(cells) >= 2:
                    key = cells[0].get_text(strip=True).rstrip(':')
                    value = cells[1].get_text(strip=True)
                    if key and value:
                        specifics[key] = value
        
        # Alternative: check definition lists
        dl_elements = soup.select('dl')
        for dl in dl_elements:
            dt_elements = dl.find_all('dt')
            dd_elements = dl.find_all('dd')
            
            for dt, dd in zip(dt_elements, dd_elements):
                key = dt.get_text(strip=True).rstrip(':')
                value = dd.get_text(strip=True)
                if key and value:
                    specifics[key] = value
        
        return specifics
    
    def _is_empty_product_page(self, soup: BeautifulSoup) -> bool:
        """Check if the product page is empty or invalid"""
        # Check for "Item not available" messages
        unavailable_selectors = [
            '.msgTextAlign',  # eBay's "This listing has ended" message
            '.empty',  # Empty state containers
            '.error',  # Error messages
            '.notFound',  # Not found messages
            '.itemUnavailable'  # Item unavailable messages
        ]
        
        # Check if any of the unavailable selectors are present
        if any(soup.select(selector) for selector in unavailable_selectors):
            return True
        
        # Check for specific text indicating empty page
        error_texts = [
            "this listing has ended",
            "item is no longer available",
            "no longer available on eBay",
            "sorry we couldn't find that page",
            "item not found"
        ]
        
        page_text = soup.get_text().lower()
        if any(error_text in page_text for error_text in error_texts):
            return True
        
        # Check if essential elements are missing
        essential_selectors = [
            '#itemTitle',  # Title element
            '#prcIsum',  # Price element
            '.itemAttr'  # Item attributes
        ]
        
        # If all essential selectors are missing, consider it empty
        if not any(soup.select(selector) for selector in essential_selectors):
            return True
        
        return False

    def _validate_ebay_url(self, url: str) -> bool:
        """Validate that a URL is a proper eBay item URL"""
        if not url:
            return False
        
        # Check basic URL structure
        if not url.startswith('http'):
            return False
        
        # Parse the URL
        try:
            parsed = urlparse(url)
            if not parsed.netloc.endswith('ebay.com'):
                return False
            
            # Check path contains /itm/ for item pages
            if '/itm/' not in parsed.path:
                return False
                
            return True
        except:
            return False

    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract full description text"""
        selectors = [
            '#desc_div',
            '.item-description',
            '[data-testid="description"]',
            '.description',
            '#item_description'
        ]
        
        # Try each description selector
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Get text with some structure preserved
                description = element.get_text(separator='\n', strip=True)
                if description and len(description) > 20:
                    # Limit description length
                    return description[:5000]
        
        return None