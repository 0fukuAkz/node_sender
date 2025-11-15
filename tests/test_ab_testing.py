"""
Tests for A/B testing functionality
"""

import pytest
from unittest.mock import Mock
from src.email_dispatcher.ab_testing import ABTestManager
from src.email_dispatcher.types import ABTestConfig
from src.email_dispatcher.exceptions import ConfigurationError


@pytest.fixture
def ab_test_config() -> ABTestConfig:
    """Fixture for A/B test configuration."""
    return {
        'test_name': 'Subject Line Test',
        'control_variant': 'control',
        'variants': [
            {
                'name': 'control',
                'weight': 0.5,
                'template_path': 'templates/message.html',
                'subject': 'Original Subject',
                'metadata': {}
            },
            {
                'name': 'variant_a',
                'weight': 0.5,
                'template_path': 'templates/message.html',
                'subject': 'New Subject',
                'metadata': {}
            }
        ]
    }


class TestABTestManager:
    """Tests for ABTestManager class."""
    
    def test_initialization(self, ab_test_config):
        """Test A/B test manager initialization."""
        manager = ABTestManager(config=ab_test_config)
        
        assert manager.test_name == 'Subject Line Test'
        assert manager.control_variant == 'control'
        assert len(manager.variants) == 2
    
    def test_validation_no_variants_raises_error(self):
        """Test initialization with no variants raises error."""
        config: ABTestConfig = {
            'test_name': 'Test',
            'control_variant': 'control',
            'variants': []
        }
        
        with pytest.raises(ConfigurationError):
            ABTestManager(config=config)
    
    def test_validation_duplicate_names_raises_error(self, ab_test_config):
        """Test initialization with duplicate variant names raises error."""
        ab_test_config['variants'].append(ab_test_config['variants'][0])  # Duplicate
        
        with pytest.raises(ConfigurationError):
            ABTestManager(config=ab_test_config)
    
    def test_validation_weights_sum_not_one(self, ab_test_config):
        """Test initialization with weights not summing to 1.0 raises error."""
        ab_test_config['variants'][0]['weight'] = 0.3
        ab_test_config['variants'][1]['weight'] = 0.3  # Sum = 0.6, not 1.0
        
        with pytest.raises(ConfigurationError):
            ABTestManager(config=ab_test_config)
    
    def test_validation_invalid_control_variant(self, ab_test_config):
        """Test initialization with invalid control variant raises error."""
        ab_test_config['control_variant'] = 'nonexistent'
        
        with pytest.raises(ConfigurationError):
            ABTestManager(config=ab_test_config)
    
    def test_assign_variant(self, ab_test_config):
        """Test assigning variant to email."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        variant = manager.assign_variant(email)
        
        assert variant['name'] in ['control', 'variant_a']
        assert manager.get_variant_for_email(email) == variant['name']
    
    def test_assign_variant_consistent(self, ab_test_config):
        """Test same email gets same variant on multiple calls."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        variant1 = manager.assign_variant(email)
        variant2 = manager.assign_variant(email)
        
        assert variant1['name'] == variant2['name']
    
    def test_force_variant_assignment(self, ab_test_config):
        """Test forcing specific variant assignment."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        variant = manager.assign_variant(email, force_variant='variant_a')
        
        assert variant['name'] == 'variant_a'
    
    def test_record_send_success(self, ab_test_config):
        """Test recording successful send."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        manager.assign_variant(email, force_variant='control')
        manager.record_send(email, success=True)
        
        results = manager.get_results()
        assert results['control']['sent'] == 1
        assert results['control']['failed'] == 0
    
    def test_record_send_failure(self, ab_test_config):
        """Test recording failed send."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        manager.assign_variant(email, force_variant='control')
        manager.record_send(email, success=False)
        
        results = manager.get_results()
        assert results['control']['sent'] == 0
        assert results['control']['failed'] == 1
    
    def test_record_open(self, ab_test_config):
        """Test recording email open."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        manager.assign_variant(email, force_variant='control')
        manager.record_send(email, success=True)
        manager.record_open(email)
        
        results = manager.get_results()
        assert results['control']['opens'] == 1
    
    def test_record_click(self, ab_test_config):
        """Test recording email click."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        manager.assign_variant(email, force_variant='control')
        manager.record_send(email, success=True)
        manager.record_click(email)
        
        results = manager.get_results()
        assert results['control']['clicks'] == 1
    
    def test_record_conversion(self, ab_test_config):
        """Test recording conversion."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        manager.assign_variant(email, force_variant='control')
        manager.record_send(email, success=True)
        manager.record_conversion(email)
        
        results = manager.get_results()
        assert results['control']['conversions'] == 1
    
    def test_get_results_with_metrics(self, ab_test_config):
        """Test getting results with calculated metrics."""
        manager = ABTestManager(config=ab_test_config)
        
        # Simulate campaign
        for i in range(10):
            email = f'user{i}@example.com'
            manager.assign_variant(email, force_variant='control')
            manager.record_send(email, success=True)
            
            if i < 7:  # 70% open rate
                manager.record_open(email)
                
                if i < 3:  # ~43% click rate of opens
                    manager.record_click(email)
                    
                    if i < 1:  # ~33% conversion rate of clicks
                        manager.record_conversion(email)
        
        results = manager.get_results()
        control = results['control']
        
        assert control['sent'] == 10
        assert control['open_rate'] == 0.7
        assert control['click_rate'] == 0.3
        assert control['conversion_rate'] == 0.1
    
    def test_get_winner(self, ab_test_config):
        """Test determining winning variant."""
        manager = ABTestManager(config=ab_test_config)
        
        # Control variant
        for i in range(10):
            email = f'control{i}@example.com'
            manager.assign_variant(email, force_variant='control')
            manager.record_send(email, success=True)
            if i < 3:  # 30% conversion
                manager.record_conversion(email)
        
        # Variant A
        for i in range(10):
            email = f'variant{i}@example.com'
            manager.assign_variant(email, force_variant='variant_a')
            manager.record_send(email, success=True)
            if i < 5:  # 50% conversion
                manager.record_conversion(email)
        
        winner = manager.get_winner(metric='conversion_rate')
        
        assert winner == 'variant_a'
    
    def test_export_results(self, ab_test_config):
        """Test exporting test results."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        manager.assign_variant(email)
        manager.record_send(email, success=True)
        
        export = manager.export_results()
        
        assert export['test_name'] == 'Subject Line Test'
        assert export['control_variant'] == 'control'
        assert 'variants' in export
        assert 'results' in export
        assert 'assignments' in export
    
    def test_format_summary(self, ab_test_config):
        """Test formatting results summary."""
        manager = ABTestManager(config=ab_test_config)
        
        email = 'test@example.com'
        manager.assign_variant(email, force_variant='control')
        manager.record_send(email, success=True)
        manager.record_open(email)
        
        summary = manager.format_summary()
        
        assert 'Subject Line Test' in summary
        assert 'control' in summary
        assert 'Open Rate' in summary
    
    def test_weighted_distribution(self, ab_test_config):
        """Test variant assignment follows weight distribution."""
        manager = ABTestManager(config=ab_test_config)
        
        # Assign 100 emails
        assignments = {}
        for i in range(100):
            email = f'user{i}@example.com'
            variant = manager.assign_variant(email)
            assignments[variant['name']] = assignments.get(variant['name'], 0) + 1
        
        # With 50/50 weights, expect roughly 50/50 distribution
        # Allow some variance (40-60%)
        assert 40 <= assignments.get('control', 0) <= 60
        assert 40 <= assignments.get('variant_a', 0) <= 60
    
    def test_statistical_significance(self, ab_test_config):
        """Test statistical significance calculation."""
        manager = ABTestManager(config=ab_test_config)
        
        # Create significant difference
        # Control: 10% conversion
        for i in range(100):
            email = f'control{i}@example.com'
            manager.assign_variant(email, force_variant='control')
            manager.record_send(email, success=True)
            if i < 10:
                manager.record_conversion(email)
        
        # Variant A: 30% conversion
        for i in range(100):
            email = f'variant{i}@example.com'
            manager.assign_variant(email, force_variant='variant_a')
            manager.record_send(email, success=True)
            if i < 30:
                manager.record_conversion(email)
        
        p_value = manager.get_statistical_significance(
            'control',
            'variant_a',
            metric='conversion_rate'
        )
        
        assert p_value is not None
        assert p_value < 0.05  # Significant difference

