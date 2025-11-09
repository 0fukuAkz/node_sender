"""
Persistent retry queue with exponential backoff for failed emails
"""

import time
import random
import threading
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass, asdict
from queue import PriorityQueue
import json
from pathlib import Path
from .exceptions import RetryQueueError, SMTPTransientError, SMTPPermanentError


@dataclass
class RetryItem:
    """Represents an email that needs to be retried."""
    email_address: str
    retry_count: int
    last_error: str
    next_retry_time: float
    max_retries: int
    original_data: Dict
    priority: int = 0
    
    def __lt__(self, other):
        """Compare by next_retry_time for priority queue."""
        return self.next_retry_time < other.next_retry_time


class RetryQueue:
    """
    Thread-safe persistent retry queue with exponential backoff.
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 60.0,
        max_delay: float = 3600.0,
        jitter: bool = True,
        persistence_path: Optional[str] = None
    ):
        """
        Initialize retry queue.
        
        Args:
            max_retries: Maximum retry attempts per email
            base_delay: Base delay in seconds for exponential backoff
            max_delay: Maximum delay between retries
            jitter: Add random jitter to prevent thundering herd
            persistence_path: Path to save queue state (None = no persistence)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.persistence_path = persistence_path
        
        self.queue: PriorityQueue = PriorityQueue()
        self.lock = threading.Lock()
        
        # Dead letter queue for permanently failed items
        self.dead_letter_queue: List[RetryItem] = []
        
        # Statistics
        self.stats = {
            'total_added': 0,
            'total_retried': 0,
            'total_succeeded': 0,
            'total_failed_permanently': 0,
            'current_size': 0,
        }
        self.stats_lock = threading.Lock()
        
        # Load persisted queue if available
        if self.persistence_path:
            self._load_from_disk()
    
    def _calculate_backoff(self, retry_count: int) -> float:
        """
        Calculate exponential backoff delay.
        
        Args:
            retry_count: Number of retries so far
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * 2^retry_count
        delay = self.base_delay * (2 ** retry_count)
        delay = min(delay, self.max_delay)
        
        # Add jitter (±25% random variation)
        if self.jitter:
            jitter_amount = delay * 0.25
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(0, delay)
    
    def add(
        self,
        email_address: str,
        error: str,
        original_data: Dict,
        retry_count: int = 0,
        priority: int = 0
    ) -> bool:
        """
        Add email to retry queue.
        
        Args:
            email_address: Email address that failed
            error: Error message
            original_data: Original email data for retry
            retry_count: Current retry count
            priority: Priority level (lower = higher priority)
            
        Returns:
            True if added, False if max retries exceeded
        """
        with self.stats_lock:
            self.stats['total_added'] += 1
        
        # Check if max retries exceeded
        if retry_count >= self.max_retries:
            self._add_to_dead_letter_queue(
                email_address, error, original_data, retry_count
            )
            with self.stats_lock:
                self.stats['total_failed_permanently'] += 1
            return False
        
        # Calculate next retry time
        delay = self._calculate_backoff(retry_count)
        next_retry_time = time.time() + delay
        
        # Create retry item
        item = RetryItem(
            email_address=email_address,
            retry_count=retry_count,
            last_error=error,
            next_retry_time=next_retry_time,
            max_retries=self.max_retries,
            original_data=original_data,
            priority=priority
        )
        
        # Add to queue
        self.queue.put((next_retry_time, item))
        
        with self.stats_lock:
            self.stats['current_size'] = self.queue.qsize()
        
        # Persist if configured
        if self.persistence_path:
            self._save_to_disk()
        
        return True
    
    def get_ready_items(self, max_items: Optional[int] = None) -> List[RetryItem]:
        """
        Get items that are ready for retry.
        
        Args:
            max_items: Maximum number of items to return (None = all ready)
            
        Returns:
            List of retry items ready for processing
        """
        ready_items = []
        now = time.time()
        
        # Collect ready items
        temp_items = []
        while not self.queue.empty():
            try:
                next_time, item = self.queue.get_nowait()
                
                if next_time <= now:
                    ready_items.append(item)
                    if max_items and len(ready_items) >= max_items:
                        # Put remaining items back
                        self.queue.put((next_time, item))
                        break
                else:
                    # Not ready yet, put back
                    temp_items.append((next_time, item))
            except Exception:
                break
        
        # Put back items that weren't ready
        for item in temp_items:
            self.queue.put(item)
        
        with self.stats_lock:
            self.stats['current_size'] = self.queue.qsize()
            self.stats['total_retried'] += len(ready_items)
        
        return ready_items
    
    def report_success(self, email_address: str) -> None:
        """
        Report successful retry.
        
        Args:
            email_address: Email that was successfully sent
        """
        with self.stats_lock:
            self.stats['total_succeeded'] += 1
    
    def report_failure(
        self,
        email_address: str,
        error: str,
        original_data: Dict,
        retry_count: int,
        is_permanent: bool = False
    ) -> bool:
        """
        Report failed retry attempt.
        
        Args:
            email_address: Email that failed
            error: Error message
            original_data: Original email data
            retry_count: Current retry count
            is_permanent: True if error is permanent (don't retry)
            
        Returns:
            True if will retry, False if giving up
        """
        if is_permanent:
            self._add_to_dead_letter_queue(
                email_address, error, original_data, retry_count
            )
            with self.stats_lock:
                self.stats['total_failed_permanently'] += 1
            return False
        
        return self.add(email_address, error, original_data, retry_count + 1)
    
    def _add_to_dead_letter_queue(
        self,
        email_address: str,
        error: str,
        original_data: Dict,
        retry_count: int
    ) -> None:
        """Add item to dead letter queue for permanently failed emails."""
        with self.lock:
            item = RetryItem(
                email_address=email_address,
                retry_count=retry_count,
                last_error=error,
                next_retry_time=0,
                max_retries=self.max_retries,
                original_data=original_data
            )
            self.dead_letter_queue.append(item)
    
    def get_dead_letter_items(self) -> List[RetryItem]:
        """Get all items from dead letter queue."""
        with self.lock:
            return self.dead_letter_queue.copy()
    
    def clear_dead_letter_queue(self) -> None:
        """Clear the dead letter queue."""
        with self.lock:
            self.dead_letter_queue.clear()
    
    def size(self) -> int:
        """Get current queue size."""
        return self.queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self.queue.empty()
    
    def get_stats(self) -> Dict[str, any]:
        """Get queue statistics."""
        with self.stats_lock:
            stats = self.stats.copy()
        
        stats['dead_letter_size'] = len(self.dead_letter_queue)
        stats['queue_size'] = self.size()
        
        return stats
    
    def _save_to_disk(self) -> None:
        """Persist queue state to disk."""
        if not self.persistence_path:
            return
        
        try:
            # Ensure directory exists
            Path(self.persistence_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Collect all items
            items = []
            temp_items = []
            while not self.queue.empty():
                try:
                    next_time, item = self.queue.get_nowait()
                    temp_items.append((next_time, item))
                    items.append(asdict(item))
                except Exception:
                    break
            
            # Put items back
            for item_tuple in temp_items:
                self.queue.put(item_tuple)
            
            # Save to file
            state = {
                'items': items,
                'dead_letter': [asdict(item) for item in self.dead_letter_queue],
                'stats': self.stats.copy(),
                'timestamp': time.time()
            }
            
            with open(self.persistence_path, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            # Don't fail on persistence errors
            pass
    
    def _load_from_disk(self) -> None:
        """Load queue state from disk."""
        if not self.persistence_path or not Path(self.persistence_path).exists():
            return
        
        try:
            with open(self.persistence_path, 'r') as f:
                state = json.load(f)
            
            # Restore items
            for item_dict in state.get('items', []):
                item = RetryItem(**item_dict)
                self.queue.put((item.next_retry_time, item))
            
            # Restore dead letter queue
            for item_dict in state.get('dead_letter', []):
                self.dead_letter_queue.append(RetryItem(**item_dict))
            
            # Restore stats (but reset some counters)
            saved_stats = state.get('stats', {})
            self.stats['total_failed_permanently'] = saved_stats.get('total_failed_permanently', 0)
            self.stats['current_size'] = self.queue.qsize()
            
        except Exception as e:
            raise RetryQueueError(f"Failed to load retry queue from disk: {e}")


class RetryProcessor:
    """
    Background processor for retry queue.
    """
    
    def __init__(
        self,
        retry_queue: RetryQueue,
        process_func: Callable[[RetryItem], bool],
        check_interval: float = 10.0
    ):
        """
        Initialize retry processor.
        
        Args:
            retry_queue: RetryQueue instance to process
            process_func: Function to process retry items (returns True on success)
            check_interval: Interval in seconds to check for ready items
        """
        self.retry_queue = retry_queue
        self.process_func = process_func
        self.check_interval = check_interval
        
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self) -> None:
        """Start background processing."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._process_loop, daemon=True)
        self.thread.start()
    
    def stop(self) -> None:
        """Stop background processing."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
    
    def _process_loop(self) -> None:
        """Background processing loop."""
        while self.running:
            try:
                # Get ready items
                ready_items = self.retry_queue.get_ready_items()
                
                # Process each item
                for item in ready_items:
                    try:
                        success = self.process_func(item)
                        
                        if success:
                            self.retry_queue.report_success(item.email_address)
                        else:
                            # Failed, re-add to queue
                            self.retry_queue.report_failure(
                                item.email_address,
                                item.last_error,
                                item.original_data,
                                item.retry_count
                            )
                    except Exception as e:
                        # Process error, re-add to queue
                        self.retry_queue.report_failure(
                            item.email_address,
                            str(e),
                            item.original_data,
                            item.retry_count
                        )
                
                # Sleep before next check
                time.sleep(self.check_interval)
                
            except Exception:
                # Don't let processor crash
                time.sleep(self.check_interval)

