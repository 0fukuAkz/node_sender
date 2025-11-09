"""
Thread-safe rate limiter with token bucket algorithm for production-scale email campaigns
"""

import threading
import time
from typing import Optional, Tuple
from .exceptions import RateLimitError


class TokenBucket:
    """
    Thread-safe token bucket implementation for rate limiting.
    
    The token bucket algorithm allows for burst traffic while maintaining
    an average rate limit over time.
    """
    
    def __init__(self, rate: float, capacity: Optional[float] = None):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket (defaults to rate for 1 second burst)
        """
        self.rate = rate
        self.capacity = capacity if capacity is not None else rate
        self.tokens = self.capacity
        self.last_update = time.monotonic()
        self.lock = threading.Lock()
    
    def consume(self, tokens: float = 1.0, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Consume tokens from the bucket.
        
        Args:
            tokens: Number of tokens to consume
            block: If True, wait until tokens available
            timeout: Maximum time to wait (None = infinite)
            
        Returns:
            True if tokens consumed, False if not enough tokens and block=False
            
        Raises:
            RateLimitError: If timeout exceeded while waiting
        """
        start_time = time.monotonic()
        
        while True:
            with self.lock:
                now = time.monotonic()
                elapsed = now - self.last_update
                
                # Add tokens based on elapsed time
                self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
                self.last_update = now
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                if not block:
                    return False
                
                # Calculate wait time for required tokens
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate
            
            # Check timeout
            if timeout is not None:
                elapsed_total = time.monotonic() - start_time
                if elapsed_total >= timeout:
                    raise RateLimitError(f"Timeout waiting for rate limit tokens after {timeout}s")
                wait_time = min(wait_time, timeout - elapsed_total)
            
            # Sleep outside the lock
            time.sleep(wait_time)
    
    def get_tokens(self) -> float:
        """Get current number of tokens (thread-safe read)."""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            return min(self.capacity, self.tokens + elapsed * self.rate)


class RateLimiter:
    """
    Production-grade thread-safe rate limiter with multiple limits and adaptive throttling.
    """
    
    def __init__(
        self,
        rate_per_minute: int = 0,
        rate_per_hour: int = 0,
        burst_allowance: float = 1.0,
        adaptive: bool = True
    ):
        """
        Initialize rate limiter.
        
        Args:
            rate_per_minute: Maximum operations per minute (0 = unlimited)
            rate_per_hour: Maximum operations per hour (0 = unlimited)
            burst_allowance: Multiplier for burst capacity (1.0 = no burst)
            adaptive: Enable adaptive rate limiting based on errors
        """
        self.rate_per_minute = rate_per_minute
        self.rate_per_hour = rate_per_hour
        self.adaptive = adaptive
        
        # Create token buckets
        self.minute_bucket = None
        self.hour_bucket = None
        
        if rate_per_minute > 0:
            rate_per_second = rate_per_minute / 60.0
            capacity = rate_per_second * burst_allowance
            self.minute_bucket = TokenBucket(rate_per_second, capacity)
        
        if rate_per_hour > 0:
            rate_per_second = rate_per_hour / 3600.0
            capacity = rate_per_second * 60 * burst_allowance  # Allow 1 minute burst
            self.hour_bucket = TokenBucket(rate_per_second, capacity)
        
        # Adaptive rate limiting state
        self.cooldown_until = 0.0
        self.cooldown_lock = threading.Lock()
        self.error_count = 0
        self.last_error_time = 0.0
        self.error_window = 60.0  # 1 minute error window
    
    def acquire(self, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire permission to perform rate-limited operation.
        
        Args:
            block: If True, wait until permission granted
            timeout: Maximum time to wait
            
        Returns:
            True if permission granted, False otherwise
            
        Raises:
            RateLimitError: If in cooldown or timeout exceeded
        """
        # Check cooldown
        if self.adaptive:
            with self.cooldown_lock:
                now = time.monotonic()
                if now < self.cooldown_until:
                    if not block:
                        return False
                    wait_time = self.cooldown_until - now
                    if timeout is not None and wait_time > timeout:
                        raise RateLimitError(f"In cooldown for {wait_time:.1f}s")
                    time.sleep(wait_time)
        
        # Acquire from both buckets if they exist
        if self.minute_bucket:
            if not self.minute_bucket.consume(1.0, block, timeout):
                return False
        
        if self.hour_bucket:
            if not self.hour_bucket.consume(1.0, block, timeout):
                return False
        
        return True
    
    def report_error(self, is_rate_limit_error: bool = False) -> None:
        """
        Report an error for adaptive rate limiting.
        
        Args:
            is_rate_limit_error: True if error was due to rate limiting
        """
        if not self.adaptive:
            return
        
        with self.cooldown_lock:
            now = time.monotonic()
            
            # Reset error count if outside window
            if now - self.last_error_time > self.error_window:
                self.error_count = 0
            
            self.error_count += 1
            self.last_error_time = now
            
            # Apply cooldown for rate limit errors
            if is_rate_limit_error:
                # Exponential backoff: 2^n seconds, max 5 minutes
                cooldown_duration = min(2 ** min(self.error_count, 8), 300)
                self.cooldown_until = now + cooldown_duration
    
    def report_success(self) -> None:
        """Report successful operation (reduces error count)."""
        if not self.adaptive:
            return
        
        with self.cooldown_lock:
            if self.error_count > 0:
                self.error_count = max(0, self.error_count - 1)
    
    def get_status(self) -> dict:
        """
        Get current rate limiter status.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'rate_per_minute': self.rate_per_minute,
            'rate_per_hour': self.rate_per_hour,
            'adaptive': self.adaptive,
        }
        
        if self.minute_bucket:
            status['minute_tokens_available'] = self.minute_bucket.get_tokens()
        
        if self.hour_bucket:
            status['hour_tokens_available'] = self.hour_bucket.get_tokens()
        
        if self.adaptive:
            with self.cooldown_lock:
                now = time.monotonic()
                status['error_count'] = self.error_count
                status['in_cooldown'] = now < self.cooldown_until
                if now < self.cooldown_until:
                    status['cooldown_remaining'] = self.cooldown_until - now
        
        return status


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    """
    
    CLOSED = 'closed'  # Normal operation
    OPEN = 'open'      # Failing, reject requests
    HALF_OPEN = 'half_open'  # Testing if recovered
    
    def __init__(
        self,
        failure_threshold: int = 10,
        timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening
            timeout: Seconds before attempting recovery
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = self.CLOSED
        self.lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """
        Call function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments to function
            
        Returns:
            Function result
            
        Raises:
            RateLimitError: If circuit is open
            Original exception: If function fails
        """
        with self.lock:
            if self.state == self.OPEN:
                now = time.monotonic()
                if now - self.last_failure_time >= self.timeout:
                    self.state = self.HALF_OPEN
                else:
                    raise RateLimitError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self) -> None:
        """Handle successful call."""
        with self.lock:
            self.failure_count = 0
            if self.state == self.HALF_OPEN:
                self.state = self.CLOSED
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            
            if self.failure_count >= self.failure_threshold:
                self.state = self.OPEN
    
    def get_state(self) -> str:
        """Get current circuit breaker state."""
        with self.lock:
            return self.state

