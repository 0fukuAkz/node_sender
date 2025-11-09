"""
Real-time metrics collection and progress reporting for email campaigns
"""

import time
import threading
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import deque


@dataclass
class Metrics:
    """Container for campaign metrics."""
    
    # Counters
    total_processed: int = 0
    total_success: int = 0
    total_failed: int = 0
    total_retries: int = 0
    total_suppressed: int = 0
    total_invalid: int = 0
    
    # Timing
    start_time: float = field(default_factory=time.time)
    last_update_time: float = field(default_factory=time.time)
    
    # Rate tracking
    success_rate_window: deque = field(default_factory=lambda: deque(maxlen=100))
    failure_rate_window: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Connection pool stats
    pool_hits: int = 0
    pool_misses: int = 0
    
    # Rate limiting stats
    rate_limit_waits: int = 0
    total_wait_time: float = 0.0
    
    def reset(self):
        """Reset all metrics."""
        self.total_processed = 0
        self.total_success = 0
        self.total_failed = 0
        self.total_retries = 0
        self.total_suppressed = 0
        self.total_invalid = 0
        self.start_time = time.time()
        self.last_update_time = time.time()
        self.success_rate_window.clear()
        self.failure_rate_window.clear()
        self.pool_hits = 0
        self.pool_misses = 0
        self.rate_limit_waits = 0
        self.total_wait_time = 0.0


class MetricsCollector:
    """
    Thread-safe metrics collector for email campaigns.
    """
    
    def __init__(self, total_emails: int = 0):
        """
        Initialize metrics collector.
        
        Args:
            total_emails: Total number of emails to process
        """
        self.metrics = Metrics()
        self.total_emails = total_emails
        self.lock = threading.Lock()
        
        # Error tracking
        self.error_types: Dict[str, int] = {}
        self.error_lock = threading.Lock()
    
    def record_success(self) -> None:
        """Record successful email send."""
        now = time.time()
        with self.lock:
            self.metrics.total_success += 1
            self.metrics.total_processed += 1
            self.metrics.last_update_time = now
            self.metrics.success_rate_window.append(now)
    
    def record_failure(self, error_type: Optional[str] = None) -> None:
        """
        Record failed email send.
        
        Args:
            error_type: Type/category of error
        """
        now = time.time()
        with self.lock:
            self.metrics.total_failed += 1
            self.metrics.total_processed += 1
            self.metrics.last_update_time = now
            self.metrics.failure_rate_window.append(now)
        
        # Track error type
        if error_type:
            with self.error_lock:
                self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
    
    def record_retry(self) -> None:
        """Record retry attempt."""
        with self.lock:
            self.metrics.total_retries += 1
    
    def record_suppressed(self) -> None:
        """Record suppressed email."""
        with self.lock:
            self.metrics.total_suppressed += 1
            self.metrics.total_processed += 1
    
    def record_invalid(self) -> None:
        """Record invalid email address."""
        with self.lock:
            self.metrics.total_invalid += 1
            self.metrics.total_processed += 1
    
    def record_pool_hit(self) -> None:
        """Record connection pool hit."""
        with self.lock:
            self.metrics.pool_hits += 1
    
    def record_pool_miss(self) -> None:
        """Record connection pool miss."""
        with self.lock:
            self.metrics.pool_misses += 1
    
    def record_rate_limit_wait(self, wait_time: float) -> None:
        """
        Record rate limit wait.
        
        Args:
            wait_time: Time waited in seconds
        """
        with self.lock:
            self.metrics.rate_limit_waits += 1
            self.metrics.total_wait_time += wait_time
    
    def get_success_rate(self) -> float:
        """
        Get current success rate (0.0 to 1.0).
        
        Returns:
            Success rate
        """
        with self.lock:
            total = self.metrics.total_success + self.metrics.total_failed
            if total == 0:
                return 0.0
            return self.metrics.total_success / total
    
    def get_failure_rate(self) -> float:
        """
        Get current failure rate (0.0 to 1.0).
        
        Returns:
            Failure rate
        """
        return 1.0 - self.get_success_rate()
    
    def get_throughput(self, window_seconds: float = 60.0) -> float:
        """
        Get current throughput (emails per second).
        
        Args:
            window_seconds: Time window for calculation
            
        Returns:
            Emails per second
        """
        now = time.time()
        cutoff = now - window_seconds
        
        with self.lock:
            recent_success = sum(1 for t in self.metrics.success_rate_window if t > cutoff)
            recent_failure = sum(1 for t in self.metrics.failure_rate_window if t > cutoff)
            recent_total = recent_success + recent_failure
            
            if window_seconds == 0:
                return 0.0
            
            return recent_total / window_seconds
    
    def get_eta(self) -> Optional[float]:
        """
        Get estimated time to completion in seconds.
        
        Returns:
            ETA in seconds or None if cannot calculate
        """
        throughput = self.get_throughput()
        
        if throughput == 0:
            return None
        
        with self.lock:
            remaining = self.total_emails - self.metrics.total_processed
            if remaining <= 0:
                return 0.0
            
            return remaining / throughput
    
    def get_elapsed_time(self) -> float:
        """
        Get elapsed time since start in seconds.
        
        Returns:
            Elapsed seconds
        """
        with self.lock:
            return time.time() - self.metrics.start_time
    
    def get_progress_percent(self) -> float:
        """
        Get progress percentage (0.0 to 100.0).
        
        Returns:
            Progress percentage
        """
        if self.total_emails == 0:
            return 0.0
        
        with self.lock:
            return (self.metrics.total_processed / self.total_emails) * 100.0
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get comprehensive metrics summary.
        
        Returns:
            Dictionary with all metrics
        """
        with self.lock:
            metrics_copy = {
                'total_emails': self.total_emails,
                'total_processed': self.metrics.total_processed,
                'total_success': self.metrics.total_success,
                'total_failed': self.metrics.total_failed,
                'total_retries': self.metrics.total_retries,
                'total_suppressed': self.metrics.total_suppressed,
                'total_invalid': self.metrics.total_invalid,
                'start_time': self.metrics.start_time,
                'last_update_time': self.metrics.last_update_time,
            }
        
        # Calculate derived metrics
        metrics_copy['success_rate'] = self.get_success_rate()
        metrics_copy['failure_rate'] = self.get_failure_rate()
        metrics_copy['throughput_per_second'] = self.get_throughput()
        metrics_copy['throughput_per_minute'] = self.get_throughput() * 60
        metrics_copy['elapsed_seconds'] = self.get_elapsed_time()
        metrics_copy['progress_percent'] = self.get_progress_percent()
        metrics_copy['eta_seconds'] = self.get_eta()
        
        # Pool stats
        with self.lock:
            total_pool_requests = self.metrics.pool_hits + self.metrics.pool_misses
            if total_pool_requests > 0:
                metrics_copy['pool_hit_rate'] = self.metrics.pool_hits / total_pool_requests
            else:
                metrics_copy['pool_hit_rate'] = 0.0
            
            metrics_copy['pool_hits'] = self.metrics.pool_hits
            metrics_copy['pool_misses'] = self.metrics.pool_misses
        
        # Rate limiting stats
        with self.lock:
            metrics_copy['rate_limit_waits'] = self.metrics.rate_limit_waits
            metrics_copy['total_wait_time'] = self.metrics.total_wait_time
            if self.metrics.rate_limit_waits > 0:
                metrics_copy['avg_wait_time'] = (
                    self.metrics.total_wait_time / self.metrics.rate_limit_waits
                )
            else:
                metrics_copy['avg_wait_time'] = 0.0
        
        # Error breakdown
        with self.error_lock:
            metrics_copy['error_types'] = self.error_types.copy()
        
        return metrics_copy
    
    def format_summary(self) -> str:
        """
        Format metrics summary as human-readable string.
        
        Returns:
            Formatted summary string
        """
        summary = self.get_summary()
        
        lines = [
            "Campaign Metrics Summary",
            "=" * 50,
            f"Progress: {summary['total_processed']}/{summary['total_emails']} "
            f"({summary['progress_percent']:.1f}%)",
            f"Success: {summary['total_success']} ({summary['success_rate']*100:.1f}%)",
            f"Failed: {summary['total_failed']} ({summary['failure_rate']*100:.1f}%)",
            f"Retries: {summary['total_retries']}",
            f"Suppressed: {summary['total_suppressed']}",
            f"Invalid: {summary['total_invalid']}",
            "",
            f"Throughput: {summary['throughput_per_minute']:.1f} emails/minute",
            f"Elapsed: {summary['elapsed_seconds']:.1f} seconds",
        ]
        
        if summary['eta_seconds'] is not None:
            lines.append(f"ETA: {summary['eta_seconds']:.1f} seconds")
        
        if summary['pool_hits'] + summary['pool_misses'] > 0:
            lines.extend([
                "",
                f"Connection Pool Hit Rate: {summary['pool_hit_rate']*100:.1f}%"
            ])
        
        if summary['rate_limit_waits'] > 0:
            lines.extend([
                "",
                f"Rate Limit Waits: {summary['rate_limit_waits']}",
                f"Avg Wait Time: {summary['avg_wait_time']:.2f}s"
            ])
        
        if summary['error_types']:
            lines.extend(["", "Error Breakdown:"])
            for error_type, count in sorted(
                summary['error_types'].items(), 
                key=lambda x: x[1], 
                reverse=True
            ):
                lines.append(f"  {error_type}: {count}")
        
        return "\n".join(lines)


class ProgressBar:
    """
    Simple console progress bar.
    """
    
    def __init__(
        self,
        total: int,
        width: int = 50,
        prefix: str = "Progress",
        show_eta: bool = True
    ):
        """
        Initialize progress bar.
        
        Args:
            total: Total items to process
            width: Width of progress bar in characters
            prefix: Prefix text
            show_eta: Show estimated time to completion
        """
        self.total = total
        self.width = width
        self.prefix = prefix
        self.show_eta = show_eta
        self.current = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def update(self, current: int) -> None:
        """
        Update progress bar.
        
        Args:
            current: Current progress count
        """
        with self.lock:
            self.current = current
            self._render()
    
    def increment(self, amount: int = 1) -> None:
        """
        Increment progress.
        
        Args:
            amount: Amount to increment
        """
        with self.lock:
            self.current += amount
            self._render()
    
    def _render(self) -> None:
        """Render progress bar to console."""
        if self.total == 0:
            percent = 0.0
        else:
            percent = self.current / self.total
        
        filled = int(self.width * percent)
        bar = '█' * filled + '-' * (self.width - filled)
        
        # Calculate ETA
        eta_str = ""
        if self.show_eta and self.current > 0:
            elapsed = time.time() - self.start_time
            rate = self.current / elapsed
            if rate > 0:
                remaining = (self.total - self.current) / rate
                eta_str = f" ETA: {remaining:.0f}s"
        
        # Print progress bar (with carriage return to overwrite)
        print(
            f'\r{self.prefix}: [{bar}] {percent*100:.1f}% '
            f'({self.current}/{self.total}){eta_str}',
            end='',
            flush=True
        )
        
        # Print newline when complete
        if self.current >= self.total:
            print()
    
    def finish(self) -> None:
        """Mark progress bar as finished."""
        with self.lock:
            self.current = self.total
            self._render()

