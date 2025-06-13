"""
Utilities Package
Contains utility modules for rate limiting and user agent management.
"""

# Import rate limiting related classes from rate_limiter module
from .rate_limiter import RateLimiter, AdaptiveRateLimiter

# Import user agent related classes from user_agents module
from .user_agents import UserAgentRotator, SmartUserAgentRotator

# Define public interface for the package
# These are the names that will be available when importing from the package
__all__ = [
    "RateLimiter",           # Basic rate limiting functionality
    "AdaptiveRateLimiter",   # Rate limiter that adjusts based on conditions
    "UserAgentRotator",      # Basic user agent rotation
    "SmartUserAgentRotator"  # Advanced user agent rotation with additional features
]