"""
State management for progress persistence and resume capability
"""

import sqlite3
import threading
import json
import time
from typing import List, Dict, Optional, Set
from enum import Enum
from pathlib import Path
from .exceptions import StateError


class EmailState(Enum):
    """Email processing states."""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    SENT = 'sent'
    FAILED = 'failed'
    RETRYING = 'retrying'
    SUPPRESSED = 'suppressed'
    INVALID = 'invalid'


class StateManager:
    """
    Thread-safe state manager for tracking email campaign progress.
    Enables resume capability and progress persistence.
    """
    
    def __init__(self, db_path: str = 'logs/state.db', campaign_id: Optional[str] = None):
        """
        Initialize state manager.
        
        Args:
            db_path: Path to SQLite database file
            campaign_id: Unique campaign identifier (auto-generated if None)
        """
        self.db_path = db_path
        self.campaign_id = campaign_id or self._generate_campaign_id()
        self.lock = threading.Lock()
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    @staticmethod
    def _generate_campaign_id() -> str:
        """Generate unique campaign ID."""
        return f"campaign_{int(time.time())}_{id(threading.current_thread())}"
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create campaigns table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS campaigns (
                        id TEXT PRIMARY KEY,
                        start_time REAL NOT NULL,
                        end_time REAL,
                        total_emails INTEGER DEFAULT 0,
                        completed_emails INTEGER DEFAULT 0,
                        failed_emails INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'running',
                        config TEXT,
                        created_at REAL DEFAULT (strftime('%s', 'now'))
                    )
                ''')
                
                # Create email_states table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS email_states (
                        campaign_id TEXT NOT NULL,
                        email_address TEXT NOT NULL,
                        state TEXT NOT NULL,
                        retry_count INTEGER DEFAULT 0,
                        last_error TEXT,
                        last_updated REAL DEFAULT (strftime('%s', 'now')),
                        metadata TEXT,
                        PRIMARY KEY (campaign_id, email_address),
                        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                    )
                ''')
                
                # Create checkpoints table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        campaign_id TEXT NOT NULL,
                        checkpoint_id INTEGER NOT NULL,
                        timestamp REAL NOT NULL,
                        processed_count INTEGER NOT NULL,
                        success_count INTEGER NOT NULL,
                        failure_count INTEGER NOT NULL,
                        PRIMARY KEY (campaign_id, checkpoint_id),
                        FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
                    )
                ''')
                
                # Create indexes for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_email_states_state 
                    ON email_states(campaign_id, state)
                ''')
                
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_email_states_updated 
                    ON email_states(campaign_id, last_updated)
                ''')
                
                conn.commit()
                
        except sqlite3.Error as e:
            raise StateError(f"Failed to initialize database: {e}")
    
    def start_campaign(self, total_emails: int, config: Optional[Dict] = None) -> None:
        """
        Start new campaign.
        
        Args:
            total_emails: Total number of emails in campaign
            config: Campaign configuration dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO campaigns 
                    (id, start_time, total_emails, status, config)
                    VALUES (?, ?, ?, 'running', ?)
                ''', (
                    self.campaign_id,
                    time.time(),
                    total_emails,
                    json.dumps(config) if config else None
                ))
                conn.commit()
        except sqlite3.Error as e:
            raise StateError(f"Failed to start campaign: {e}")
    
    def end_campaign(self, status: str = 'completed') -> None:
        """
        Mark campaign as ended.
        
        Args:
            status: Final campaign status
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE campaigns 
                    SET end_time = ?, status = ?
                    WHERE id = ?
                ''', (time.time(), status, self.campaign_id))
                conn.commit()
        except sqlite3.Error as e:
            raise StateError(f"Failed to end campaign: {e}")
    
    def add_emails(self, email_addresses: List[str], initial_state: EmailState = EmailState.PENDING) -> None:
        """
        Add emails to campaign.
        
        Args:
            email_addresses: List of email addresses
            initial_state: Initial state for emails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT OR IGNORE INTO email_states 
                    (campaign_id, email_address, state, last_updated)
                    VALUES (?, ?, ?, ?)
                ''', [(
                    self.campaign_id,
                    email,
                    initial_state.value,
                    time.time()
                ) for email in email_addresses])
                conn.commit()
        except sqlite3.Error as e:
            raise StateError(f"Failed to add emails: {e}")
    
    def update_email_state(
        self,
        email_address: str,
        state: EmailState,
        error: Optional[str] = None,
        increment_retry: bool = False,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Update email state.
        
        Args:
            email_address: Email address to update
            state: New state
            error: Error message if failed
            increment_retry: Whether to increment retry count
            metadata: Additional metadata dictionary
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if increment_retry:
                    cursor.execute('''
                        UPDATE email_states 
                        SET state = ?, 
                            retry_count = retry_count + 1,
                            last_error = ?,
                            last_updated = ?,
                            metadata = ?
                        WHERE campaign_id = ? AND email_address = ?
                    ''', (
                        state.value,
                        error,
                        time.time(),
                        json.dumps(metadata) if metadata else None,
                        self.campaign_id,
                        email_address
                    ))
                else:
                    cursor.execute('''
                        UPDATE email_states 
                        SET state = ?,
                            last_error = ?,
                            last_updated = ?,
                            metadata = ?
                        WHERE campaign_id = ? AND email_address = ?
                    ''', (
                        state.value,
                        error,
                        time.time(),
                        json.dumps(metadata) if metadata else None,
                        self.campaign_id,
                        email_address
                    ))
                
                # Update campaign statistics
                if state == EmailState.SENT:
                    cursor.execute('''
                        UPDATE campaigns 
                        SET completed_emails = completed_emails + 1
                        WHERE id = ?
                    ''', (self.campaign_id,))
                elif state == EmailState.FAILED:
                    cursor.execute('''
                        UPDATE campaigns 
                        SET failed_emails = failed_emails + 1
                        WHERE id = ?
                    ''', (self.campaign_id,))
                
                conn.commit()
        except sqlite3.Error as e:
            raise StateError(f"Failed to update email state: {e}")
    
    def get_emails_by_state(self, state: EmailState) -> List[str]:
        """
        Get all email addresses in specific state.
        
        Args:
            state: State to filter by
            
        Returns:
            List of email addresses
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT email_address 
                    FROM email_states 
                    WHERE campaign_id = ? AND state = ?
                ''', (self.campaign_id, state.value))
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.Error as e:
            raise StateError(f"Failed to get emails by state: {e}")
    
    def get_email_state(self, email_address: str) -> Optional[Dict]:
        """
        Get state information for specific email.
        
        Args:
            email_address: Email address to query
            
        Returns:
            Dictionary with state information or None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT state, retry_count, last_error, last_updated, metadata
                    FROM email_states 
                    WHERE campaign_id = ? AND email_address = ?
                ''', (self.campaign_id, email_address))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'state': row[0],
                        'retry_count': row[1],
                        'last_error': row[2],
                        'last_updated': row[3],
                        'metadata': json.loads(row[4]) if row[4] else None
                    }
                return None
        except sqlite3.Error as e:
            raise StateError(f"Failed to get email state: {e}")
    
    def create_checkpoint(self, checkpoint_id: int) -> None:
        """
        Create progress checkpoint.
        
        Args:
            checkpoint_id: Checkpoint identifier
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current counts
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN state = 'sent' THEN 1 ELSE 0 END) as success,
                        SUM(CASE WHEN state = 'failed' THEN 1 ELSE 0 END) as failure
                    FROM email_states
                    WHERE campaign_id = ?
                ''', (self.campaign_id,))
                
                row = cursor.fetchone()
                total, success, failure = row[0], row[1] or 0, row[2] or 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO checkpoints
                    (campaign_id, checkpoint_id, timestamp, processed_count, 
                     success_count, failure_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    self.campaign_id,
                    checkpoint_id,
                    time.time(),
                    total,
                    success,
                    failure
                ))
                
                conn.commit()
        except sqlite3.Error as e:
            raise StateError(f"Failed to create checkpoint: {e}")
    
    def get_statistics(self) -> Dict[str, any]:
        """
        Get campaign statistics.
        
        Returns:
            Dictionary with statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get campaign info
                cursor.execute('''
                    SELECT total_emails, completed_emails, failed_emails, 
                           start_time, end_time, status
                    FROM campaigns
                    WHERE id = ?
                ''', (self.campaign_id,))
                
                campaign = cursor.fetchone()
                
                # Get state counts
                cursor.execute('''
                    SELECT state, COUNT(*) as count
                    FROM email_states
                    WHERE campaign_id = ?
                    GROUP BY state
                ''', (self.campaign_id,))
                
                state_counts = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Get retry statistics
                cursor.execute('''
                    SELECT 
                        AVG(retry_count) as avg_retries,
                        MAX(retry_count) as max_retries
                    FROM email_states
                    WHERE campaign_id = ? AND retry_count > 0
                ''', (self.campaign_id,))
                
                retry_stats = cursor.fetchone()
                
                stats = {
                    'campaign_id': self.campaign_id,
                    'total_emails': campaign[0] if campaign else 0,
                    'completed_emails': campaign[1] if campaign else 0,
                    'failed_emails': campaign[2] if campaign else 0,
                    'start_time': campaign[3] if campaign else None,
                    'end_time': campaign[4] if campaign else None,
                    'status': campaign[5] if campaign else 'unknown',
                    'state_counts': state_counts,
                    'avg_retries': retry_stats[0] if retry_stats[0] else 0,
                    'max_retries': retry_stats[1] if retry_stats[1] else 0,
                }
                
                # Calculate progress
                if stats['total_emails'] > 0:
                    processed = stats['completed_emails'] + stats['failed_emails']
                    stats['progress_percent'] = (processed / stats['total_emails']) * 100
                else:
                    stats['progress_percent'] = 0
                
                # Calculate elapsed time
                if stats['start_time']:
                    end = stats['end_time'] or time.time()
                    stats['elapsed_seconds'] = end - stats['start_time']
                
                return stats
                
        except sqlite3.Error as e:
            raise StateError(f"Failed to get statistics: {e}")
    
    def can_resume(self) -> bool:
        """
        Check if campaign can be resumed.
        
        Returns:
            True if campaign has pending/failed emails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM email_states
                    WHERE campaign_id = ? 
                    AND state IN ('pending', 'failed', 'retrying')
                ''', (self.campaign_id,))
                count = cursor.fetchone()[0]
                return count > 0
        except sqlite3.Error as e:
            raise StateError(f"Failed to check resume capability: {e}")
    
    def cleanup_old_campaigns(self, days: int = 30) -> int:
        """
        Clean up campaigns older than specified days.
        
        Args:
            days: Number of days to keep
            
        Returns:
            Number of campaigns deleted
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cutoff_time = time.time() - (days * 86400)
                
                # Get campaigns to delete
                cursor.execute('''
                    SELECT id FROM campaigns
                    WHERE start_time < ? AND status IN ('completed', 'failed', 'cancelled')
                ''', (cutoff_time,))
                
                campaign_ids = [row[0] for row in cursor.fetchall()]
                
                # Delete associated data
                for cid in campaign_ids:
                    cursor.execute('DELETE FROM email_states WHERE campaign_id = ?', (cid,))
                    cursor.execute('DELETE FROM checkpoints WHERE campaign_id = ?', (cid,))
                    cursor.execute('DELETE FROM campaigns WHERE id = ?', (cid,))
                
                conn.commit()
                return len(campaign_ids)
                
        except sqlite3.Error as e:
            raise StateError(f"Failed to cleanup old campaigns: {e}")

