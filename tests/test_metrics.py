"""
Unit tests for metrics collection
"""

import pytest
import time
from src.email_dispatcher.metrics import MetricsCollector, ProgressBar


class TestMetricsCollector:
    """Test MetricsCollector."""
    
    def test_init(self):
        """Test metrics collector initialization."""
        metrics = MetricsCollector(total_emails=100)
        assert metrics.total_emails == 100
        assert metrics.metrics.total_success == 0
        assert metrics.metrics.total_failed == 0
    
    def test_record_success(self):
        """Test recording successful email."""
        metrics = MetricsCollector(total_emails=100)
        metrics.record_success()
        
        assert metrics.metrics.total_success == 1
        assert metrics.metrics.total_processed == 1
    
    def test_record_failure(self):
        """Test recording failed email."""
        metrics = MetricsCollector(total_emails=100)
        metrics.record_failure('smtp_error')
        
        assert metrics.metrics.total_failed == 1
        assert metrics.metrics.total_processed == 1
        assert 'smtp_error' in metrics.error_types
    
    def test_success_rate(self):
        """Test success rate calculation."""
        metrics = MetricsCollector(total_emails=100)
        
        for _ in range(7):
            metrics.record_success()
        for _ in range(3):
            metrics.record_failure()
        
        assert abs(metrics.get_success_rate() - 0.7) < 0.001
        assert abs(metrics.get_failure_rate() - 0.3) < 0.001
    
    def test_progress_percent(self):
        """Test progress percentage calculation."""
        metrics = MetricsCollector(total_emails=100)
        
        for _ in range(25):
            metrics.record_success()
        
        assert metrics.get_progress_percent() == 25.0
    
    def test_summary(self):
        """Test getting metrics summary."""
        metrics = MetricsCollector(total_emails=100)
        metrics.record_success()
        metrics.record_failure('test_error')
        
        summary = metrics.get_summary()
        
        assert summary['total_emails'] == 100
        assert summary['total_success'] == 1
        assert summary['total_failed'] == 1
        assert 'success_rate' in summary
        assert 'throughput_per_second' in summary


class TestProgressBar:
    """Test ProgressBar."""
    
    def test_init(self):
        """Test progress bar initialization."""
        bar = ProgressBar(total=100, width=50)
        assert bar.total == 100
        assert bar.width == 50
        assert bar.current == 0
    
    def test_update(self):
        """Test updating progress."""
        bar = ProgressBar(total=100)
        bar.update(50)
        assert bar.current == 50
    
    def test_increment(self):
        """Test incrementing progress."""
        bar = ProgressBar(total=100)
        bar.increment(10)
        bar.increment(5)
        assert bar.current == 15
    
    def test_finish(self):
        """Test finishing progress bar."""
        bar = ProgressBar(total=100)
        bar.finish()
        assert bar.current == 100

