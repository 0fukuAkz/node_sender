"""
Unit tests for identity generation
"""

import pytest
from src.email_dispatcher.identity import generate_identity


class TestIdentity:
    """Test identity generation."""
    
    def test_generate_identity(self):
        """Test generating random identity."""
        identity = generate_identity()
        
        assert 'full_name' in identity
        assert 'email' in identity
        assert 'company' in identity
        assert 'uuid' in identity
        assert 'from_field' in identity
    
    def test_identity_fields_not_empty(self):
        """Test that all identity fields have values."""
        identity = generate_identity()
        
        for key, value in identity.items():
            assert value is not None
            assert len(str(value)) > 0
    
    def test_email_format(self):
        """Test that generated email has valid format."""
        identity = generate_identity()
        email = identity['email']
        
        assert '@' in email
        assert '.' in email
        assert email.endswith('.com')
    
    def test_uuid_uniqueness(self):
        """Test that UUIDs are unique."""
        identities = [generate_identity() for _ in range(100)]
        uuids = [i['uuid'] for i in identities]
        
        assert len(uuids) == len(set(uuids))  # All unique

