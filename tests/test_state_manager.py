"""
Unit tests for state manager
"""

import pytest
import os
import tempfile
from src.email_dispatcher.state_manager import StateManager, EmailState


class TestStateManager:
    """Test StateManager."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
            db_path = f.name
        
        yield db_path
        
        try:
            os.unlink(db_path)
        except:
            pass
    
    def test_init(self, temp_db):
        """Test state manager initialization."""
        sm = StateManager(db_path=temp_db, campaign_id='test_campaign')
        assert sm.campaign_id == 'test_campaign'
        assert sm.db_path == temp_db
    
    def test_start_campaign(self, temp_db):
        """Test starting new campaign."""
        sm = StateManager(db_path=temp_db, campaign_id='test_campaign')
        sm.start_campaign(total_emails=100, config={'test': 'value'})
        
        stats = sm.get_statistics()
        assert stats['total_emails'] == 100
        assert stats['status'] == 'running'
    
    def test_add_emails(self, temp_db):
        """Test adding emails to campaign."""
        sm = StateManager(db_path=temp_db, campaign_id='test_campaign')
        sm.start_campaign(total_emails=3)
        
        emails = ['test1@example.com', 'test2@example.com', 'test3@example.com']
        sm.add_emails(emails, EmailState.PENDING)
        
        pending = sm.get_emails_by_state(EmailState.PENDING)
        assert len(pending) == 3
    
    def test_update_email_state(self, temp_db):
        """Test updating email state."""
        sm = StateManager(db_path=temp_db, campaign_id='test_campaign')
        sm.start_campaign(total_emails=1)
        
        email = 'test@example.com'
        sm.add_emails([email], EmailState.PENDING)
        sm.update_email_state(email, EmailState.SENT)
        
        state = sm.get_email_state(email)
        assert state['state'] == 'sent'
    
    def test_create_checkpoint(self, temp_db):
        """Test creating checkpoint."""
        sm = StateManager(db_path=temp_db, campaign_id='test_campaign')
        sm.start_campaign(total_emails=100)
        sm.add_emails(['test@example.com'], EmailState.SENT)
        
        sm.create_checkpoint(checkpoint_id=1)
        # Should not raise exception
    
    def test_get_statistics(self, temp_db):
        """Test getting campaign statistics."""
        sm = StateManager(db_path=temp_db, campaign_id='test_campaign')
        sm.start_campaign(total_emails=10)
        
        emails = [f'test{i}@example.com' for i in range(10)]
        sm.add_emails(emails, EmailState.PENDING)
        
        for i, email in enumerate(emails):
            if i < 7:
                sm.update_email_state(email, EmailState.SENT)
            else:
                sm.update_email_state(email, EmailState.FAILED)
        
        stats = sm.get_statistics()
        assert stats['completed_emails'] == 7
        assert stats['failed_emails'] == 3
    
    def test_can_resume(self, temp_db):
        """Test checking if campaign can be resumed."""
        sm = StateManager(db_path=temp_db, campaign_id='test_campaign')
        sm.start_campaign(total_emails=2)
        
        sm.add_emails(['pending@example.com'], EmailState.PENDING)
        sm.add_emails(['sent@example.com'], EmailState.SENT)
        
        assert sm.can_resume() is True

