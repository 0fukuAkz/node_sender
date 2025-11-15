"""
Analytics and reporting for email campaigns
"""

import sqlite3
import threading
import time
import json
from typing import List, Dict, Optional, Any
from pathlib import Path
from logging import Logger

from .types import AnalyticsEvent, ReportData, CampaignStats


class AnalyticsCollector:
    """Collects and stores analytics events for email campaigns."""
    
    def __init__(
        self,
        db_path: str = 'logs/analytics.db',
        logger: Optional[Logger] = None
    ):
        """
        Initialize analytics collector.
        
        Args:
            db_path: Path to SQLite database
            logger: Logger instance
        """
        self.db_path = db_path
        self.logger = logger
        self.lock = threading.Lock()
        
        # Ensure directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize analytics database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    email_address TEXT NOT NULL,
                    campaign_id TEXT NOT NULL,
                    variant_name TEXT,
                    metadata TEXT,
                    created_at REAL DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_campaign
                ON events(campaign_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_email
                ON events(email_address)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_type
                ON events(event_type)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_events_timestamp
                ON events(timestamp)
            ''')
            
            # Campaign metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS campaign_metrics (
                    campaign_id TEXT PRIMARY KEY,
                    total_sent INTEGER DEFAULT 0,
                    total_failed INTEGER DEFAULT 0,
                    total_opens INTEGER DEFAULT 0,
                    total_clicks INTEGER DEFAULT 0,
                    total_conversions INTEGER DEFAULT 0,
                    total_bounces INTEGER DEFAULT 0,
                    total_complaints INTEGER DEFAULT 0,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    metadata TEXT,
                    updated_at REAL DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            # Variant metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS variant_metrics (
                    campaign_id TEXT NOT NULL,
                    variant_name TEXT NOT NULL,
                    total_sent INTEGER DEFAULT 0,
                    total_failed INTEGER DEFAULT 0,
                    total_opens INTEGER DEFAULT 0,
                    total_clicks INTEGER DEFAULT 0,
                    total_conversions INTEGER DEFAULT 0,
                    metadata TEXT,
                    PRIMARY KEY (campaign_id, variant_name)
                )
            ''')
            
            conn.commit()
    
    def track_event(self, event: AnalyticsEvent) -> None:
        """
        Track an analytics event.
        
        Args:
            event: Analytics event data
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        INSERT INTO events (
                            event_type, timestamp, email_address,
                            campaign_id, variant_name, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        event['event_type'],
                        event['timestamp'],
                        event['email_address'],
                        event['campaign_id'],
                        event.get('variant_name'),
                        json.dumps(event.get('metadata', {}))
                    ))
                    
                    conn.commit()
                    
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Failed to track event: {e}")
    
    def track_send(
        self,
        email: str,
        campaign_id: str,
        success: bool = True,
        variant_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Track email send event.
        
        Args:
            email: Email address
            campaign_id: Campaign identifier
            success: Whether send was successful
            variant_name: Variant name (for A/B tests)
            metadata: Additional metadata
        """
        event_type = 'send_success' if success else 'send_failure'
        
        self.track_event({
            'event_type': event_type,
            'timestamp': time.time(),
            'email_address': email,
            'campaign_id': campaign_id,
            'variant_name': variant_name,
            'metadata': metadata or {}
        })
    
    def track_open(
        self,
        email: str,
        campaign_id: str,
        variant_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track email open event."""
        self.track_event({
            'event_type': 'open',
            'timestamp': time.time(),
            'email_address': email,
            'campaign_id': campaign_id,
            'variant_name': variant_name,
            'metadata': metadata or {}
        })
    
    def track_click(
        self,
        email: str,
        campaign_id: str,
        variant_name: Optional[str] = None,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track email click event."""
        meta = metadata or {}
        if url:
            meta['url'] = url
        
        self.track_event({
            'event_type': 'click',
            'timestamp': time.time(),
            'email_address': email,
            'campaign_id': campaign_id,
            'variant_name': variant_name,
            'metadata': meta
        })
    
    def track_conversion(
        self,
        email: str,
        campaign_id: str,
        variant_name: Optional[str] = None,
        value: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track conversion event."""
        meta = metadata or {}
        if value is not None:
            meta['value'] = value
        
        self.track_event({
            'event_type': 'conversion',
            'timestamp': time.time(),
            'email_address': email,
            'campaign_id': campaign_id,
            'variant_name': variant_name,
            'metadata': meta
        })
    
    def track_bounce(
        self,
        email: str,
        campaign_id: str,
        bounce_type: str = 'hard',
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track bounce event."""
        meta = metadata or {}
        meta['bounce_type'] = bounce_type
        
        self.track_event({
            'event_type': 'bounce',
            'timestamp': time.time(),
            'email_address': email,
            'campaign_id': campaign_id,
            'variant_name': None,
            'metadata': meta
        })
    
    def track_complaint(
        self,
        email: str,
        campaign_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track spam complaint event."""
        self.track_event({
            'event_type': 'complaint',
            'timestamp': time.time(),
            'email_address': email,
            'campaign_id': campaign_id,
            'variant_name': None,
            'metadata': metadata or {}
        })
    
    def get_campaign_stats(self, campaign_id: str) -> CampaignStats:
        """
        Get statistics for a campaign.
        
        Args:
            campaign_id: Campaign identifier
            
        Returns:
            Campaign statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Count events by type
            cursor.execute('''
                SELECT event_type, COUNT(*) as count
                FROM events
                WHERE campaign_id = ?
                GROUP BY event_type
            ''', (campaign_id,))
            
            event_counts = dict(cursor.fetchall())
            
            # Get time range
            cursor.execute('''
                SELECT MIN(timestamp), MAX(timestamp)
                FROM events
                WHERE campaign_id = ?
            ''', (campaign_id,))
            
            start_time, end_time = cursor.fetchone()
            
            return {
                'total_emails': event_counts.get('send_success', 0) + event_counts.get('send_failure', 0),
                'completed_emails': event_counts.get('send_success', 0),
                'failed_emails': event_counts.get('send_failure', 0),
                'pending_emails': 0,
                'elapsed_seconds': (end_time - start_time) if start_time and end_time else 0
            }
    
    def get_variant_stats(
        self,
        campaign_id: str,
        variant_name: str
    ) -> Dict[str, Any]:
        """
        Get statistics for a specific variant.
        
        Args:
            campaign_id: Campaign identifier
            variant_name: Variant name
            
        Returns:
            Variant statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT event_type, COUNT(*) as count
                FROM events
                WHERE campaign_id = ? AND variant_name = ?
                GROUP BY event_type
            ''', (campaign_id, variant_name))
            
            event_counts = dict(cursor.fetchall())
            
            sent = event_counts.get('send_success', 0)
            
            return {
                'sent': sent,
                'failed': event_counts.get('send_failure', 0),
                'opens': event_counts.get('open', 0),
                'clicks': event_counts.get('click', 0),
                'conversions': event_counts.get('conversion', 0),
                'open_rate': event_counts.get('open', 0) / sent if sent > 0 else 0,
                'click_rate': event_counts.get('click', 0) / sent if sent > 0 else 0,
                'conversion_rate': event_counts.get('conversion', 0) / sent if sent > 0 else 0
            }
    
    def generate_report(
        self,
        campaign_id: str,
        include_variants: bool = True
    ) -> ReportData:
        """
        Generate comprehensive campaign report.
        
        Args:
            campaign_id: Campaign identifier
            include_variants: Include variant breakdown
            
        Returns:
            Report data
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get overall stats
            cursor.execute('''
                SELECT event_type, COUNT(*) as count
                FROM events
                WHERE campaign_id = ?
                GROUP BY event_type
            ''', (campaign_id,))
            
            event_counts = dict(cursor.fetchall())
            
            # Get time range
            cursor.execute('''
                SELECT MIN(timestamp), MAX(timestamp)
                FROM events
                WHERE campaign_id = ?
            ''', (campaign_id,))
            
            start_time, end_time = cursor.fetchone()
            
            sent = event_counts.get('send_success', 0)
            failed = event_counts.get('send_failure', 0)
            total = sent + failed
            
            report: ReportData = {
                'campaign_id': campaign_id,
                'start_time': start_time or 0,
                'end_time': end_time or 0,
                'total_sent': sent,
                'total_failed': failed,
                'success_rate': sent / total if total > 0 else 0,
                'avg_send_time': 0,
                'variants': [],
                'errors': []
            }
            
            # Get variant stats if requested
            if include_variants:
                cursor.execute('''
                    SELECT DISTINCT variant_name
                    FROM events
                    WHERE campaign_id = ? AND variant_name IS NOT NULL
                ''', (campaign_id,))
                
                variants = [row[0] for row in cursor.fetchall()]
                
                for variant in variants:
                    stats = self.get_variant_stats(campaign_id, variant)
                    stats['name'] = variant
                    report['variants'].append(stats)
            
            # Get error breakdown
            cursor.execute('''
                SELECT metadata, COUNT(*) as count
                FROM events
                WHERE campaign_id = ? AND event_type = 'send_failure'
                GROUP BY metadata
                LIMIT 10
            ''', (campaign_id,))
            
            for metadata_json, count in cursor.fetchall():
                try:
                    metadata = json.loads(metadata_json) if metadata_json else {}
                    report['errors'].append({
                        'error_type': metadata.get('error_type', 'unknown'),
                        'count': count
                    })
                except:
                    pass
            
            return report
    
    def export_events(
        self,
        campaign_id: str,
        output_path: str,
        format: str = 'json'
    ) -> None:
        """
        Export events to file.
        
        Args:
            campaign_id: Campaign identifier
            output_path: Output file path
            format: Export format ('json' or 'csv')
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT event_type, timestamp, email_address,
                       variant_name, metadata
                FROM events
                WHERE campaign_id = ?
                ORDER BY timestamp
            ''', (campaign_id,))
            
            events = cursor.fetchall()
            
            if format == 'json':
                data = [
                    {
                        'event_type': row[0],
                        'timestamp': row[1],
                        'email': row[2],
                        'variant': row[3],
                        'metadata': json.loads(row[4]) if row[4] else {}
                    }
                    for row in events
                ]
                
                with open(output_path, 'w') as f:
                    json.dump(data, f, indent=2)
            
            elif format == 'csv':
                import csv
                
                with open(output_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'event_type', 'timestamp', 'email',
                        'variant', 'metadata'
                    ])
                    writer.writerows(events)
    
    def get_time_series(
        self,
        campaign_id: str,
        event_type: str,
        interval_seconds: int = 3600
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for an event type.
        
        Args:
            campaign_id: Campaign identifier
            event_type: Type of event
            interval_seconds: Time interval for buckets
            
        Returns:
            List of time series data points
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    CAST(timestamp / ? AS INTEGER) * ? as bucket,
                    COUNT(*) as count
                FROM events
                WHERE campaign_id = ? AND event_type = ?
                GROUP BY bucket
                ORDER BY bucket
            ''', (interval_seconds, interval_seconds, campaign_id, event_type))
            
            return [
                {
                    'timestamp': row[0],
                    'count': row[1]
                }
                for row in cursor.fetchall()
            ]

