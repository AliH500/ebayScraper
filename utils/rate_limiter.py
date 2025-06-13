"""
Rate Limiting Module
Handles request throttling to prevent overwhelming eBay servers.
"""

# Import standard library modules
import time  # For time-related functions
import random  # For generating random numbers
import logging  # For logging events
from typing import Optional  # For type hints


class RateLimiter:
    """Rate limiter to control request frequency"""
    
    def __init__(self, base_delay: float = 2.0, randomize: bool = True):
        """
        Initialize rate limiter
        
        Args:
            base_delay: Base delay between requests in seconds
            randomize: Whether to add random variation to delays
        """
        self.base_delay = base_delay  # Default delay between requests
        self.randomize = randomize  # Whether to randomize delays
        self.last_request_time: Optional[float] = None  # Timestamp of last request
        self.logger = logging.getLogger(__name__)  # Logger instance
        
        # Adaptive rate limiting variables
        self.consecutive_successes = 0  # Count of successful requests in a row
        self.consecutive_failures = 0  # Count of failed requests in a row
        self.current_delay = base_delay  # Current active delay value
        
    def wait(self):
        """Wait appropriate amount of time before next request"""
        current_time = time.time()  # Get current timestamp
        
        # If we've made a previous request, calculate needed delay
        if self.last_request_time is not None:
            elapsed = current_time - self.last_request_time  # Time since last request
            delay_needed = self.current_delay - elapsed  # Additional delay required
            
            if delay_needed > 0:  # If we need to wait
                if self.randomize:
                    # Add random variation (±25%) to prevent pattern detection
                    variation = delay_needed * 0.25
                    actual_delay = delay_needed + random.uniform(-variation, variation)
                    actual_delay = max(0.1, actual_delay)  # Minimum 0.1 second delay
                else:
                    actual_delay = delay_needed
                
                self.logger.debug(f"Rate limiting: waiting {actual_delay:.2f} seconds")
                time.sleep(actual_delay)  # Pause execution
        
        self.last_request_time = time.time()  # Update last request time
    
    def on_success(self):
        """Call this when a request succeeds"""
        self.consecutive_successes += 1  # Increment success counter
        self.consecutive_failures = 0  # Reset failure counter
        
        # Gradually decrease delay after consecutive successes
        if self.consecutive_successes >= 5:
            self.current_delay = max(self.base_delay * 0.8, 0.5)  # Reduce delay by 20% (min 0.5s)
            self.logger.debug(f"Reducing delay to {self.current_delay:.2f}s after {self.consecutive_successes} successes")
    
    def on_failure(self, error_type: str = "general"):
        """Call this when a request fails"""
        self.consecutive_failures += 1  # Increment failure counter
        self.consecutive_successes = 0  # Reset success counter
        
        # Increase delay based on failure type and count
        if error_type == "rate_limit" or self.consecutive_failures >= 3:
            self.current_delay = min(self.base_delay * 2, 30.0)  # Double delay (max 30s)
            self.logger.warning(f"Increasing delay to {self.current_delay:.2f}s after {self.consecutive_failures} failures")
        elif self.consecutive_failures >= 5:
            self.current_delay = min(self.base_delay * 3, 60.0)  # Triple delay (max 60s)
            self.logger.warning(f"Further increasing delay to {self.current_delay:.2f}s after repeated failures")
    
    def on_blocked(self):
        """Call this when we detect we're being blocked"""
        self.current_delay = 60.0  # Set long delay (1 minute)
        self.consecutive_failures += 10  # Treat as major failure
        self.logger.warning("Detected blocking, increasing delay to 60 seconds")
    
    def reset(self):
        """Reset rate limiter to initial state"""
        self.current_delay = self.base_delay  # Reset to base delay
        self.consecutive_successes = 0  # Reset success counter
        self.consecutive_failures = 0  # Reset failure counter
        self.last_request_time = None  # Clear last request time
        self.logger.debug("Rate limiter reset")
    
    def get_current_delay(self) -> float:
        """Get current delay setting"""
        return self.current_delay  # Return current delay value
    
    def set_delay(self, delay: float):
        """Manually set delay"""
        self.current_delay = max(0.1, delay)  # Set new delay (min 0.1s)
        self.base_delay = self.current_delay  # Update base delay
        self.logger.debug(f"Delay manually set to {self.current_delay:.2f}s")


class AdaptiveRateLimiter(RateLimiter):
    """More sophisticated rate limiter that adapts based on response patterns"""
    
    def __init__(self, base_delay: float = 2.0):
        super().__init__(base_delay, randomize=True)  # Initialize parent class
        self.response_times = []  # Store recent response times
        self.max_response_time_history = 10  # Max number of response times to track
        
    def on_request_complete(self, response_time: float, success: bool):
        """Call this when a request completes"""
        self.response_times.append(response_time)  # Record response time
        # Maintain fixed-size history
        if len(self.response_times) > self.max_response_time_history:
            self.response_times.pop(0)  # Remove oldest entry
        
        if success:
            self.on_success()  # Handle success case
            
            # If response times are consistently fast, speed up
            if len(self.response_times) >= 5:
                avg_response_time = sum(self.response_times) / len(self.response_times)
                if avg_response_time < 1.0 and self.consecutive_successes >= 5:
                    self.current_delay = max(self.current_delay * 0.9, 0.5)  # Reduce delay
        else:
            self.on_failure()  # Handle failure case
            
            # If response times are slow, slow down
            if len(self.response_times) >= 3:
                avg_response_time = sum(self.response_times[-3:]) / 3  # Recent average
                if avg_response_time > 5.0:  # If responses are slow
                    self.current_delay = min(self.current_delay * 1.5, 30.0)  # Increase delay