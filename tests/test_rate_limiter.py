"""
Unit tests for rate limiter
"""

import pytest
import time
import threading
from src.email_dispatcher.rate_limiter import TokenBucket, RateLimiter, CircuitBreaker
from src.email_dispatcher.exceptions import RateLimitError


class TestTokenBucket:
    """Test TokenBucket implementation."""
    
    def test_init(self):
        """Test bucket initialization."""
        bucket = TokenBucket(rate=10.0, capacity=20.0)
        assert bucket.rate == 10.0
        assert bucket.capacity == 20.0
        assert bucket.tokens == 20.0
    
    def test_consume_success(self):
        """Test successful token consumption."""
        bucket = TokenBucket(rate=100.0, capacity=100.0)
        result = bucket.consume(10.0, block=False)
        assert result is True
        assert bucket.tokens < 100.0
    
    def test_consume_insufficient(self):
        """Test consumption with insufficient tokens."""
        bucket = TokenBucket(rate=10.0, capacity=5.0)
        bucket.tokens = 2.0
        result = bucket.consume(10.0, block=False)
        assert result is False
    
    def test_token_refill(self):
        """Test that tokens refill over time."""
        bucket = TokenBucket(rate=10.0, capacity=10.0)
        bucket.consume(10.0, block=False)
        time.sleep(0.5)
        assert bucket.get_tokens() > 0
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
        bucket = TokenBucket(rate=100.0, capacity=100.0)
        results = []
        
        def consume_tokens():
            result = bucket.consume(1.0, block=False)
            results.append(result)
        
        threads = [threading.Thread(target=consume_tokens) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have consumed 50 tokens successfully
        assert sum(results) <= 100


class TestRateLimiter:
    """Test RateLimiter with multiple limits."""
    
    def test_init_unlimited(self):
        """Test initialization with no limits."""
        limiter = RateLimiter(rate_per_minute=0, rate_per_hour=0)
        assert limiter.minute_bucket is None
        assert limiter.hour_bucket is None
    
    def test_init_with_limits(self):
        """Test initialization with limits."""
        limiter = RateLimiter(rate_per_minute=60, rate_per_hour=3600)
        assert limiter.minute_bucket is not None
        assert limiter.hour_bucket is not None
    
    def test_acquire_success(self):
        """Test successful rate limit acquisition."""
        limiter = RateLimiter(rate_per_minute=1000)
        result = limiter.acquire(block=False)
        assert result is True
    
    def test_adaptive_error_tracking(self):
        """Test adaptive rate limiting with errors."""
        limiter = RateLimiter(rate_per_minute=100, adaptive=True)
        
        # Report multiple errors
        for _ in range(5):
            limiter.report_error(is_rate_limit_error=True)
        
        status = limiter.get_status()
        assert status['error_count'] > 0
    
    def test_success_reduces_errors(self):
        """Test that successes reduce error count."""
        limiter = RateLimiter(rate_per_minute=100, adaptive=True)
        
        limiter.report_error()
        limiter.report_error()
        assert limiter.error_count == 2
        
        limiter.report_success()
        assert limiter.error_count == 1


class TestCircuitBreaker:
    """Test CircuitBreaker pattern."""
    
    def test_init(self):
        """Test circuit breaker initialization."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60.0)
        assert cb.state == CircuitBreaker.CLOSED
        assert cb.failure_count == 0
    
    def test_successful_call(self):
        """Test successful function call."""
        cb = CircuitBreaker(failure_threshold=3)
        
        def success_func():
            return "success"
        
        result = cb.call(success_func)
        assert result == "success"
        assert cb.state == CircuitBreaker.CLOSED
    
    def test_open_on_failures(self):
        """Test circuit opens after threshold."""
        cb = CircuitBreaker(failure_threshold=3)
        
        def failing_func():
            raise Exception("Test error")
        
        # Trigger failures
        for _ in range(3):
            try:
                cb.call(failing_func)
            except Exception:
                pass
        
        assert cb.state == CircuitBreaker.OPEN
    
    def test_reject_when_open(self):
        """Test that open circuit rejects calls."""
        cb = CircuitBreaker(failure_threshold=2)
        
        def failing_func():
            raise Exception("Test error")
        
        # Open circuit
        for _ in range(2):
            try:
                cb.call(failing_func)
            except Exception:
                pass
        
        # Should raise RateLimitError
        with pytest.raises(RateLimitError):
            cb.call(failing_func)

