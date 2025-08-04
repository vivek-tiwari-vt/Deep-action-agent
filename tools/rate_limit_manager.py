#!/usr/bin/env python3
"""
Enhanced Rate Limit Manager
Provides sophisticated rate limiting with exponential backoff, jitter, and fallback strategies.
"""

import time
import random
import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import threading
from collections import defaultdict
from loguru import logger

class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    ADAPTIVE = "adaptive"

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    jitter_factor: float = 0.1
    strategy: RateLimitStrategy = RateLimitStrategy.EXPONENTIAL_BACKOFF
    success_threshold: int = 5  # Reset backoff after N successful calls

class RateLimitManager:
    """Sophisticated rate limiting manager with multiple strategies."""
    
    def __init__(self):
        self.providers = defaultdict(lambda: RateLimitConfig())
        self.provider_stats = defaultdict(lambda: {
            'success_count': 0,
            'failure_count': 0,
            'last_success': None,
            'last_failure': None,
            'current_backoff': 0,
            'consecutive_failures': 0
        })
        self.lock = threading.Lock()
        self.callback = None
        
    def configure_provider(self, provider: str, config: RateLimitConfig):
        """Configure rate limiting for a specific provider."""
        self.providers[provider] = config
        
    def add_callback(self, callback: Callable[[str, str, float], None]):
        """Add a callback for rate limit events."""
        self.callback = callback
        
    def _notify_callback(self, provider: str, event: str, delay: float):
        """Notify callback of rate limit events."""
        if self.callback:
            try:
                self.callback(provider, event, delay)
            except Exception as e:
                logger.error(f"Rate limit callback error: {e}")
    
    def _calculate_delay(self, provider: str, attempt: int) -> float:
        """Calculate delay based on strategy and attempt number."""
        config = self.providers[provider]
        stats = self.provider_stats[provider]
        
        if config.strategy == RateLimitStrategy.EXPONENTIAL_BACKOFF:
            delay = min(config.base_delay * (2 ** attempt), config.max_delay)
        elif config.strategy == RateLimitStrategy.LINEAR_BACKOFF:
            delay = min(config.base_delay * attempt, config.max_delay)
        elif config.strategy == RateLimitStrategy.FIXED_DELAY:
            delay = config.base_delay
        elif config.strategy == RateLimitStrategy.ADAPTIVE:
            # Adaptive strategy based on failure rate
            failure_rate = stats['failure_count'] / max(stats['success_count'] + stats['failure_count'], 1)
            if failure_rate > 0.5:
                delay = min(config.base_delay * (2 ** attempt), config.max_delay)
            else:
                delay = config.base_delay
        else:
            delay = config.base_delay
            
        # Add jitter to prevent thundering herd
        jitter = delay * config.jitter_factor * random.uniform(-1, 1)
        delay = max(0, delay + jitter)
        
        return delay
    
    def record_success(self, provider: str):
        """Record a successful API call."""
        with self.lock:
            stats = self.provider_stats[provider]
            stats['success_count'] += 1
            stats['last_success'] = datetime.now()
            stats['consecutive_failures'] = 0
            
            # Reset backoff after success threshold
            if stats['success_count'] % self.providers[provider].success_threshold == 0:
                stats['current_backoff'] = 0
                
            logger.debug(f"Provider {provider} success recorded. Total: {stats['success_count']}")
    
    def record_failure(self, provider: str, error_type: str = "unknown"):
        """Record a failed API call."""
        with self.lock:
            stats = self.provider_stats[provider]
            stats['failure_count'] += 1
            stats['last_failure'] = datetime.now()
            stats['consecutive_failures'] += 1
            
            logger.warning(f"Provider {provider} failure recorded. Error: {error_type}. Consecutive: {stats['consecutive_failures']}")
    
    def should_skip_provider(self, provider: str) -> bool:
        """Check if provider should be skipped due to recent failures."""
        stats = self.provider_stats[provider]
        config = self.providers[provider]
        
        # Skip if too many consecutive failures
        if stats['consecutive_failures'] >= config.max_retries * 2:
            return True
            
        # Skip if last failure was very recent
        if stats['last_failure'] and (datetime.now() - stats['last_failure']).seconds < 30:
            return True
            
        return False
    
    def get_provider_health(self, provider: str) -> Dict[str, Any]:
        """Get health metrics for a provider."""
        stats = self.provider_stats[provider]
        total_calls = stats['success_count'] + stats['failure_count']
        
        return {
            'provider': provider,
            'success_rate': stats['success_count'] / max(total_calls, 1),
            'total_calls': total_calls,
            'consecutive_failures': stats['consecutive_failures'],
            'last_success': stats['last_success'],
            'last_failure': stats['last_failure'],
            'current_backoff': stats['current_backoff'],
            'is_healthy': not self.should_skip_provider(provider)
        }
    
    async def execute_with_backoff(self, func: Callable, provider: str, *args, **kwargs):
        """
        Execute a function with rate limiting and backoff.
        
        Args:
            func: Function to execute
            provider: Provider name for rate limiting
            *args, **kwargs: Arguments for the function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        config = self.providers[provider]
        last_exception = None
        
        for attempt in range(config.max_retries + 1):
            try:
                # Check if we should skip this provider
                if self.should_skip_provider(provider):
                    logger.warning(f"Skipping provider {provider} due to recent failures")
                    raise Exception(f"Provider {provider} is temporarily unavailable")
                
                # Execute the function
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                # Record success
                self.record_success(provider)
                return result
                
            except Exception as e:
                last_exception = e
                error_type = type(e).__name__
                
                # Record failure
                self.record_failure(provider, error_type)
                
                # Check if we should retry
                if attempt < config.max_retries:
                    delay = self._calculate_delay(provider, attempt)
                    
                    logger.warning(f"Provider {provider} attempt {attempt + 1} failed: {error_type}. "
                                 f"Retrying in {delay:.2f}s...")
                    
                    self._notify_callback(provider, "retry", delay)
                    
                    # Wait before retry
                    await asyncio.sleep(delay) if asyncio.iscoroutinefunction(func) else time.sleep(delay)
                else:
                    logger.error(f"Provider {provider} failed after {config.max_retries} attempts: {error_type}")
                    self._notify_callback(provider, "final_failure", 0)
        
        # All retries failed
        raise last_exception
    
    def execute_with_fallback(self, primary_func: Callable, fallback_func: Callable, 
                            primary_provider: str, fallback_provider: str, *args, **kwargs):
        """
        Execute with fallback to another provider.
        
        Args:
            primary_func: Primary function to try
            fallback_func: Fallback function to try
            primary_provider: Primary provider name
            fallback_provider: Fallback provider name
            *args, **kwargs: Arguments for the functions
            
        Returns:
            Result from either function
        """
        try:
            return self.execute_with_backoff(primary_func, primary_provider, *args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary provider {primary_provider} failed, trying fallback {fallback_provider}: {e}")
            return self.execute_with_backoff(fallback_func, fallback_provider, *args, **kwargs)
    
    def get_health_report(self) -> Dict[str, Dict[str, Any]]:
        """Get health report for all providers."""
        return {provider: self.get_provider_health(provider) for provider in self.providers}
    
    def reset_provider(self, provider: str):
        """Reset statistics for a provider."""
        with self.lock:
            self.provider_stats[provider] = {
                'success_count': 0,
                'failure_count': 0,
                'last_success': None,
                'last_failure': None,
                'current_backoff': 0,
                'consecutive_failures': 0
            }
            logger.info(f"Reset statistics for provider {provider}")
    
    def get_best_provider(self, providers: List[str]) -> Optional[str]:
        """Get the healthiest provider from a list."""
        best_provider = None
        best_score = -1
        
        for provider in providers:
            if provider not in self.providers:
                continue
                
            health = self.get_provider_health(provider)
            if not health['is_healthy']:
                continue
                
            # Score based on success rate and recent activity
            score = health['success_rate']
            if health['last_success']:
                # Bonus for recent success
                time_since_success = (datetime.now() - health['last_success']).seconds
                if time_since_success < 300:  # 5 minutes
                    score += 0.1
                    
            if score > best_score:
                best_score = score
                best_provider = provider
                
        return best_provider

# Global rate limit manager instance
rate_limit_manager = RateLimitManager()

# Configure default providers
rate_limit_manager.configure_provider('gemini', RateLimitConfig(
    max_retries=3,
    base_delay=2.0,
    max_delay=30.0,
    strategy=RateLimitStrategy.EXPONENTIAL_BACKOFF
))

rate_limit_manager.configure_provider('openrouter', RateLimitConfig(
    max_retries=3,
    base_delay=1.0,
    max_delay=15.0,
    strategy=RateLimitStrategy.EXPONENTIAL_BACKOFF
)) 