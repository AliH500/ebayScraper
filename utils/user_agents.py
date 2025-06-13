"""
User Agent Management Module
Handles rotation of user agent strings to mimic different browsers.
"""

# Import standard library modules
import random  # For random selection functionality
import logging  # For logging events
from typing import List  # For type hints


class UserAgentRotator:
    """Manages rotation of user agent strings to prevent detection"""
    
    def __init__(self):
        # Initialize logger for this class
        self.logger = logging.getLogger(__name__)
        # Load the list of user agents
        self.user_agents = self._get_user_agent_list()
        # Initialize rotation index
        self.current_index = 0
        
    def _get_user_agent_list(self) -> List[str]:
        """Get list of realistic user agent strings covering major browsers and OS"""
        return [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
            
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
            
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
            
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            
            # Firefox on Linux
            "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
        ]
    
    def get_random_agent(self) -> str:
        """Get a random user agent string from the available list"""
        agent = random.choice(self.user_agents)  # Random selection
        self.logger.debug(f"Selected user agent: {agent[:50]}...")  # Log first 50 chars
        return agent
    
    def get_next_agent(self) -> str:
        """Get the next user agent in sequential rotation"""
        agent = self.user_agents[self.current_index]  # Get current agent
        # Update index with wrap-around
        self.current_index = (self.current_index + 1) % len(self.user_agents)
        self.logger.debug(f"Rotated to user agent: {agent[:50]}...")
        return agent
    
    def add_custom_agent(self, user_agent: str):
        """Add a custom user agent to the rotation pool"""
        if user_agent not in self.user_agents:  # Avoid duplicates
            self.user_agents.append(user_agent)  # Add new agent
            self.logger.info(f"Added custom user agent: {user_agent[:50]}...")
    
    def get_agent_count(self) -> int:
        """Get total number of available user agents"""
        return len(self.user_agents)  # Return count
    
    def get_mobile_agent(self) -> str:
        """Get a mobile-specific user agent string"""
        mobile_agents = [
            # iPhone
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            
            # Android Chrome
            "Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            
            # Android Firefox
            "Mozilla/5.0 (Mobile; rv:120.0) Gecko/120.0 Firefox/120.0",
            
            # iPad
            "Mozilla/5.0 (iPad; CPU OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
        ]
        
        agent = random.choice(mobile_agents)  # Random mobile agent
        self.logger.debug(f"Selected mobile user agent: {agent[:50]}...")
        return agent
    
    def get_desktop_agent(self) -> str:
        """Get a desktop-specific user agent string"""
        # Filter out mobile identifiers
        desktop_agents = [ua for ua in self.user_agents if 'Mobile' not in ua and 'iPhone' not in ua and 'Android' not in ua]
        agent = random.choice(desktop_agents)  # Random desktop agent
        self.logger.debug(f"Selected desktop user agent: {agent[:50]}...")
        return agent


class SmartUserAgentRotator(UserAgentRotator):
    """Advanced user agent rotator that tracks success rates"""
    
    def __init__(self):
        super().__init__()  # Initialize parent class
        # Track success/failure rates per agent
        self.agent_success_rates = {}
        # Track total usage count per agent
        self.agent_usage_count = {}
        
    def get_best_agent(self) -> str:
        """Get the user agent with the highest historical success rate"""
        if not self.agent_success_rates:  # No data yet
            return self.get_random_agent()
        
        # Find agent with best success rate
        best_agent = None
        best_rate = 0
        
        for agent, stats in self.agent_success_rates.items():
            if stats['total'] >= 5:  # Only consider agents with enough uses
                rate = stats['success'] / stats['total']  # Calculate rate
                if rate > best_rate:
                    best_rate = rate
                    best_agent = agent
        
        if best_agent:  # Found a good performer
            self.logger.debug(f"Selected best performing agent (success rate: {best_rate:.2f})")
            return best_agent
        else:  # Fallback to random
            return self.get_random_agent()
    
    def record_result(self, user_agent: str, success: bool):
        """Record whether a user agent was successful or not"""
        if user_agent not in self.agent_success_rates:
            # Initialize tracking for new agent
            self.agent_success_rates[user_agent] = {'success': 0, 'total': 0}
        
        # Update statistics
        self.agent_success_rates[user_agent]['total'] += 1
        if success:
            self.agent_success_rates[user_agent]['success'] += 1
        
        # Track total usage (regardless of success)
        self.agent_usage_count[user_agent] = self.agent_usage_count.get(user_agent, 0) + 1
    
    def get_stats(self) -> dict:
        """Get detailed statistics about user agent performance"""
        stats = {}
        for agent, data in self.agent_success_rates.items():
            if data['total'] > 0:  # Only include agents with usage
                success_rate = data['success'] / data['total']  # Calculate rate
                # Store truncated agent name with stats
                stats[agent[:50] + "..."] = {
                    'success_rate': success_rate,
                    'total_uses': data['total'],
                    'successes': data['success']
                }
        return stats