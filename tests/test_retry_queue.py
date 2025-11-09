"""
Unit tests for retry queue
"""

import pytest
import time
from src.email_dispatcher.retry_queue import RetryQueue, RetryItem


class TestRetryQueue:
    """Test RetryQueue."""
    
    def test_init(self):
        """Test retry queue initialization."""
        queue = RetryQueue(max_retries=3, base_delay=60.0)
        assert queue.max_retries == 3
        assert queue.base_delay == 60.0
        assert queue.is_empty()
    
    def test_add_item(self):
        """Test adding item to queue."""
        queue = RetryQueue(max_retries=3)
        
        result = queue.add(
            email_address='test@example.com',
            error='Test error',
            original_data={'key': 'value'},
            retry_count=0
        )
        
        assert result is True
        assert not queue.is_empty()
    
    def test_max_retries_exceeded(self):
        """Test that items exceeding max retries go to dead letter queue."""
        queue = RetryQueue(max_retries=2)
        
        result = queue.add(
            email_address='test@example.com',
            error='Max retries',
            original_data={},
            retry_count=2  # Already at max
        )
        
        assert result is False
        dead_letter = queue.get_dead_letter_items()
        assert len(dead_letter) == 1
    
    def test_get_ready_items(self):
        """Test getting items ready for retry."""
        queue = RetryQueue(max_retries=3, base_delay=0.1)
        
        queue.add(
            email_address='test@example.com',
            error='Test',
            original_data={},
            retry_count=0
        )
        
        # Wait for item to be ready
        time.sleep(0.2)
        
        ready = queue.get_ready_items()
        assert len(ready) >= 1
    
    def test_report_success(self):
        """Test reporting successful retry."""
        queue = RetryQueue(max_retries=3)
        queue.report_success('test@example.com')
        
        stats = queue.get_stats()
        assert stats['total_succeeded'] == 1
    
    def test_report_failure_permanent(self):
        """Test reporting permanent failure."""
        queue = RetryQueue(max_retries=3)
        
        result = queue.report_failure(
            email_address='test@example.com',
            error='Permanent error',
            original_data={},
            retry_count=0,
            is_permanent=True
        )
        
        assert result is False
        dead_letter = queue.get_dead_letter_items()
        assert len(dead_letter) == 1
    
    def test_exponential_backoff(self):
        """Test exponential backoff calculation."""
        queue = RetryQueue(max_retries=5, base_delay=10.0, jitter=False)
        
        delay0 = queue._calculate_backoff(0)
        delay1 = queue._calculate_backoff(1)
        delay2 = queue._calculate_backoff(2)
        
        assert delay0 == 10.0
        assert delay1 == 20.0
        assert delay2 == 40.0
    
    def test_stats(self):
        """Test getting queue statistics."""
        queue = RetryQueue(max_retries=3)
        
        queue.add('test1@example.com', 'error', {}, 0)
        queue.add('test2@example.com', 'error', {}, 0)
        
        stats = queue.get_stats()
        assert stats['total_added'] == 2
        assert stats['queue_size'] > 0

