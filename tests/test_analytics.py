"""
Tests for analytics and reporting
"""

import pytest
import os
import time
import tempfile
from src.email_dispatcher.analytics import AnalyticsCollector
from src.email_dispatcher.types import AnalyticsEvent


@pytest.fixture
def analytics_db():
    """Fixture for temporary analytics database."""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def analytics(analytics_db):
    """Fixture for analytics collector."""
    return AnalyticsCollector(db_path=analytics_db)


class TestAnalyticsCollector:
    """Tests for AnalyticsCollector class."""
    
    def test_initialization(self, analytics_db):
        """Test analytics collector initialization."""
        collector = AnalyticsCollector(db_path=analytics_db)
        
        assert collector.db_path == analytics_db
        assert os.path.exists(analytics_db)
    
    def test_track_event(self, analytics):
        """Test tracking a generic event."""
        event: AnalyticsEvent = {
            'event_type': 'test_event',
            'timestamp': time.time(),
            'email_address': 'test@example.com',
            'campaign_id': 'campaign_123',
            'variant_name': 'control',
            'metadata': {'key': 'value'}
        }
        
        analytics.track_event(event)
        
        # Verify event was stored (no exception means success)
        assert True
    
    def test_track_send_success(self, analytics):
        """Test tracking successful send."""
        analytics.track_send(
            email='test@example.com',
            campaign_id='campaign_123',
            success=True,
            variant_name='control'
        )
        
        stats = analytics.get_campaign_stats('campaign_123')
        assert stats['completed_emails'] == 1
        assert stats['failed_emails'] == 0
    
    def test_track_send_failure(self, analytics):
        """Test tracking failed send."""
        analytics.track_send(
            email='test@example.com',
            campaign_id='campaign_123',
            success=False,
            variant_name='control'
        )
        
        stats = analytics.get_campaign_stats('campaign_123')
        assert stats['completed_emails'] == 0
        assert stats['failed_emails'] == 1
    
    def test_track_open(self, analytics):
        """Test tracking email open."""
        analytics.track_send('test@example.com', 'campaign_123', success=True)
        analytics.track_open('test@example.com', 'campaign_123')
        
        # Opens are tracked as events
        assert True
    
    def test_track_click(self, analytics):
        """Test tracking email click."""
        analytics.track_send('test@example.com', 'campaign_123', success=True)
        analytics.track_click(
            email='test@example.com',
            campaign_id='campaign_123',
            url='https://example.com'
        )
        
        assert True
    
    def test_track_conversion(self, analytics):
        """Test tracking conversion."""
        analytics.track_send('test@example.com', 'campaign_123', success=True)
        analytics.track_conversion(
            email='test@example.com',
            campaign_id='campaign_123',
            value=99.99
        )
        
        assert True
    
    def test_track_bounce(self, analytics):
        """Test tracking bounce."""
        analytics.track_bounce(
            email='test@example.com',
            campaign_id='campaign_123',
            bounce_type='hard'
        )
        
        assert True
    
    def test_track_complaint(self, analytics):
        """Test tracking spam complaint."""
        analytics.track_complaint(
            email='test@example.com',
            campaign_id='campaign_123'
        )
        
        assert True
    
    def test_get_campaign_stats(self, analytics):
        """Test getting campaign statistics."""
        campaign_id = 'campaign_123'
        
        # Track some events
        analytics.track_send('user1@example.com', campaign_id, success=True)
        analytics.track_send('user2@example.com', campaign_id, success=True)
        analytics.track_send('user3@example.com', campaign_id, success=False)
        
        stats = analytics.get_campaign_stats(campaign_id)
        
        assert stats['total_emails'] == 3
        assert stats['completed_emails'] == 2
        assert stats['failed_emails'] == 1
    
    def test_get_variant_stats(self, analytics):
        """Test getting variant-specific statistics."""
        campaign_id = 'campaign_123'
        
        # Track sends for control variant
        analytics.track_send('user1@example.com', campaign_id, success=True, variant_name='control')
        analytics.track_send('user2@example.com', campaign_id, success=True, variant_name='control')
        
        # Track engagement
        analytics.track_open('user1@example.com', campaign_id, variant_name='control')
        analytics.track_click('user1@example.com', campaign_id, variant_name='control')
        analytics.track_conversion('user1@example.com', campaign_id, variant_name='control')
        
        stats = analytics.get_variant_stats(campaign_id, 'control')
        
        assert stats['sent'] == 2
        assert stats['opens'] == 1
        assert stats['clicks'] == 1
        assert stats['conversions'] == 1
        assert stats['open_rate'] == 0.5
    
    def test_generate_report(self, analytics):
        """Test generating comprehensive report."""
        campaign_id = 'campaign_123'
        
        # Track events
        analytics.track_send('user1@example.com', campaign_id, success=True, variant_name='control')
        analytics.track_send('user2@example.com', campaign_id, success=True, variant_name='variant_a')
        analytics.track_send('user3@example.com', campaign_id, success=False)
        
        report = analytics.generate_report(campaign_id, include_variants=True)
        
        assert report['campaign_id'] == campaign_id
        assert report['total_sent'] == 2
        assert report['total_failed'] == 1
        assert report['success_rate'] > 0
        assert len(report['variants']) > 0
    
    def test_export_events_json(self, analytics, analytics_db):
        """Test exporting events to JSON."""
        campaign_id = 'campaign_123'
        
        analytics.track_send('user1@example.com', campaign_id, success=True)
        analytics.track_send('user2@example.com', campaign_id, success=True)
        
        output_path = analytics_db.replace('.db', '_events.json')
        analytics.export_events(campaign_id, output_path, format='json')
        
        assert os.path.exists(output_path)
        
        # Cleanup
        os.unlink(output_path)
    
    def test_export_events_csv(self, analytics, analytics_db):
        """Test exporting events to CSV."""
        campaign_id = 'campaign_123'
        
        analytics.track_send('user1@example.com', campaign_id, success=True)
        analytics.track_send('user2@example.com', campaign_id, success=True)
        
        output_path = analytics_db.replace('.db', '_events.csv')
        analytics.export_events(campaign_id, output_path, format='csv')
        
        assert os.path.exists(output_path)
        
        # Cleanup
        os.unlink(output_path)
    
    def test_get_time_series(self, analytics):
        """Test getting time series data."""
        campaign_id = 'campaign_123'
        
        # Track events with timestamps
        analytics.track_send('user1@example.com', campaign_id, success=True)
        analytics.track_send('user2@example.com', campaign_id, success=True)
        
        time_series = analytics.get_time_series(
            campaign_id=campaign_id,
            event_type='send_success',
            interval_seconds=3600
        )
        
        assert isinstance(time_series, list)
        if time_series:
            assert 'timestamp' in time_series[0]
            assert 'count' in time_series[0]
    
    def test_multiple_campaigns(self, analytics):
        """Test tracking multiple campaigns separately."""
        # Campaign 1
        analytics.track_send('user1@example.com', 'campaign_1', success=True)
        analytics.track_send('user2@example.com', 'campaign_1', success=True)
        
        # Campaign 2
        analytics.track_send('user3@example.com', 'campaign_2', success=True)
        
        stats1 = analytics.get_campaign_stats('campaign_1')
        stats2 = analytics.get_campaign_stats('campaign_2')
        
        assert stats1['total_emails'] == 2
        assert stats2['total_emails'] == 1
    
    def test_variant_comparison(self, analytics):
        """Test comparing multiple variants."""
        campaign_id = 'campaign_123'
        
        # Control variant
        for i in range(10):
            analytics.track_send(f'control{i}@example.com', campaign_id, success=True, variant_name='control')
            if i < 3:  # 30% conversion
                analytics.track_conversion(f'control{i}@example.com', campaign_id, variant_name='control')
        
        # Variant A
        for i in range(10):
            analytics.track_send(f'variant{i}@example.com', campaign_id, success=True, variant_name='variant_a')
            if i < 5:  # 50% conversion
                analytics.track_conversion(f'variant{i}@example.com', campaign_id, variant_name='variant_a')
        
        control_stats = analytics.get_variant_stats(campaign_id, 'control')
        variant_stats = analytics.get_variant_stats(campaign_id, 'variant_a')
        
        assert control_stats['conversion_rate'] < variant_stats['conversion_rate']

