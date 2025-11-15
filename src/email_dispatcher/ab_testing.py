"""
A/B testing functionality for email campaigns
"""

import random
import threading
import time
from typing import List, Dict, Optional, Any
from logging import Logger

from .types import ABTestConfig, ABTestVariant
from .exceptions import ConfigurationError


class ABTestManager:
    """Manages A/B tests for email campaigns."""
    
    def __init__(
        self,
        config: ABTestConfig,
        logger: Optional[Logger] = None
    ):
        """
        Initialize A/B test manager.
        
        Args:
            config: A/B test configuration
            logger: Logger instance
        """
        self.test_name = config['test_name']
        self.variants = config['variants']
        self.control_variant = config.get('control_variant')
        self.logger = logger
        
        # Validate configuration
        self._validate_config()
        
        # Assignment tracking
        self.assignments: Dict[str, str] = {}  # email -> variant_name
        self.variant_counts: Dict[str, int] = {v['name']: 0 for v in self.variants}
        self.lock = threading.Lock()
        
        # Results tracking
        self.variant_results: Dict[str, Dict[str, Any]] = {
            v['name']: {
                'sent': 0,
                'failed': 0,
                'opens': 0,
                'clicks': 0,
                'conversions': 0,
                'start_time': time.time()
            }
            for v in self.variants
        }
    
    def _validate_config(self) -> None:
        """Validate A/B test configuration."""
        if not self.variants:
            raise ConfigurationError("At least one variant must be defined")
        
        # Check variant names are unique
        names = [v['name'] for v in self.variants]
        if len(names) != len(set(names)):
            raise ConfigurationError("Variant names must be unique")
        
        # Validate weights sum to approximately 1.0
        total_weight = sum(v.get('weight', 0) for v in self.variants)
        if not (0.99 <= total_weight <= 1.01):
            raise ConfigurationError(f"Variant weights must sum to 1.0 (got {total_weight})")
        
        # Validate control variant exists
        if self.control_variant:
            if self.control_variant not in names:
                raise ConfigurationError(f"Control variant '{self.control_variant}' not found")
    
    def assign_variant(self, email: str, force_variant: Optional[str] = None) -> ABTestVariant:
        """
        Assign a variant to an email address.
        
        Args:
            email: Email address
            force_variant: Force specific variant (for testing)
            
        Returns:
            Assigned variant
        """
        with self.lock:
            # Check if already assigned
            if email in self.assignments:
                variant_name = self.assignments[email]
                return self._get_variant_by_name(variant_name)
            
            # Force variant if specified
            if force_variant:
                variant = self._get_variant_by_name(force_variant)
                if variant:
                    self.assignments[email] = force_variant
                    self.variant_counts[force_variant] += 1
                    return variant
            
            # Weighted random assignment
            variant = self._weighted_random_assignment()
            self.assignments[email] = variant['name']
            self.variant_counts[variant['name']] += 1
            
            if self.logger:
                self.logger.debug(
                    f"Assigned {email} to variant '{variant['name']}'",
                    extra={'variant': variant['name'], 'email': email}
                )
            
            return variant
    
    def _weighted_random_assignment(self) -> ABTestVariant:
        """
        Assign variant using weighted random selection.
        
        Returns:
            Selected variant
        """
        rand = random.random()
        cumulative = 0.0
        
        for variant in self.variants:
            cumulative += variant.get('weight', 0)
            if rand <= cumulative:
                return variant
        
        # Fallback to last variant
        return self.variants[-1]
    
    def _get_variant_by_name(self, variant_name: str) -> Optional[ABTestVariant]:
        """
        Get variant by name.
        
        Args:
            variant_name: Name of variant
            
        Returns:
            Variant or None
        """
        for variant in self.variants:
            if variant['name'] == variant_name:
                return variant
        return None
    
    def get_variant_for_email(self, email: str) -> Optional[str]:
        """
        Get assigned variant for email.
        
        Args:
            email: Email address
            
        Returns:
            Variant name or None
        """
        with self.lock:
            return self.assignments.get(email)
    
    def record_send(self, email: str, success: bool = True) -> None:
        """
        Record email send for variant.
        
        Args:
            email: Email address
            success: Whether send was successful
        """
        with self.lock:
            variant_name = self.assignments.get(email)
            if not variant_name:
                return
            
            if success:
                self.variant_results[variant_name]['sent'] += 1
            else:
                self.variant_results[variant_name]['failed'] += 1
    
    def record_open(self, email: str) -> None:
        """
        Record email open for variant.
        
        Args:
            email: Email address
        """
        with self.lock:
            variant_name = self.assignments.get(email)
            if variant_name:
                self.variant_results[variant_name]['opens'] += 1
    
    def record_click(self, email: str) -> None:
        """
        Record email click for variant.
        
        Args:
            email: Email address
        """
        with self.lock:
            variant_name = self.assignments.get(email)
            if variant_name:
                self.variant_results[variant_name]['clicks'] += 1
    
    def record_conversion(self, email: str) -> None:
        """
        Record conversion for variant.
        
        Args:
            email: Email address
        """
        with self.lock:
            variant_name = self.assignments.get(email)
            if variant_name:
                self.variant_results[variant_name]['conversions'] += 1
    
    def get_results(self) -> Dict[str, Dict[str, Any]]:
        """
        Get current test results.
        
        Returns:
            Dictionary of variant results with metrics
        """
        with self.lock:
            results = {}
            
            for variant_name, data in self.variant_results.items():
                sent = data['sent']
                failed = data['failed']
                total = sent + failed
                
                results[variant_name] = {
                    'sent': sent,
                    'failed': failed,
                    'total_attempts': total,
                    'opens': data['opens'],
                    'clicks': data['clicks'],
                    'conversions': data['conversions'],
                    'send_rate': sent / total if total > 0 else 0,
                    'open_rate': data['opens'] / sent if sent > 0 else 0,
                    'click_rate': data['clicks'] / sent if sent > 0 else 0,
                    'conversion_rate': data['conversions'] / sent if sent > 0 else 0,
                    'click_through_rate': data['clicks'] / data['opens'] if data['opens'] > 0 else 0,
                    'elapsed_time': time.time() - data['start_time']
                }
            
            return results
    
    def get_winner(self, metric: str = 'conversion_rate') -> Optional[str]:
        """
        Determine winning variant based on metric.
        
        Args:
            metric: Metric to use for comparison
            
        Returns:
            Name of winning variant or None
        """
        results = self.get_results()
        
        if not results:
            return None
        
        # Find variant with highest metric value
        winner = max(results.items(), key=lambda x: x[1].get(metric, 0))
        return winner[0]
    
    def get_statistical_significance(
        self,
        variant_a: str,
        variant_b: str,
        metric: str = 'conversion_rate'
    ) -> Optional[float]:
        """
        Calculate statistical significance between two variants.
        
        Args:
            variant_a: First variant name
            variant_b: Second variant name
            metric: Metric to compare
            
        Returns:
            P-value or None if insufficient data
            
        Note:
            This is a simplified calculation. For production use,
            consider using proper statistical libraries like scipy.
        """
        results = self.get_results()
        
        if variant_a not in results or variant_b not in results:
            return None
        
        # Get metric values
        value_a = results[variant_a].get(metric, 0)
        value_b = results[variant_b].get(metric, 0)
        
        # Get sample sizes
        n_a = results[variant_a]['sent']
        n_b = results[variant_b]['sent']
        
        if n_a == 0 or n_b == 0:
            return None
        
        # Simplified z-test calculation
        # For production, use scipy.stats or similar
        p_pooled = (value_a * n_a + value_b * n_b) / (n_a + n_b)
        se = (p_pooled * (1 - p_pooled) * (1/n_a + 1/n_b)) ** 0.5
        
        if se == 0:
            return None
        
        z_score = abs(value_a - value_b) / se
        
        # Approximate p-value (very simplified)
        # For production, use proper statistical functions
        if z_score > 2.58:
            return 0.01
        elif z_score > 1.96:
            return 0.05
        elif z_score > 1.65:
            return 0.10
        else:
            return 0.5
    
    def export_results(self) -> Dict[str, Any]:
        """
        Export complete test results.
        
        Returns:
            Dictionary with test configuration and results
        """
        return {
            'test_name': self.test_name,
            'control_variant': self.control_variant,
            'variants': [
                {
                    'name': v['name'],
                    'weight': v.get('weight', 0),
                    'template_path': v.get('template_path', ''),
                    'subject': v.get('subject', '')
                }
                for v in self.variants
            ],
            'assignments': len(self.assignments),
            'variant_distribution': self.variant_counts,
            'results': self.get_results(),
            'winner': self.get_winner(),
            'timestamp': time.time()
        }
    
    def format_summary(self) -> str:
        """
        Format results as human-readable summary.
        
        Returns:
            Formatted summary string
        """
        results = self.get_results()
        winner = self.get_winner()
        
        lines = [
            f"A/B Test: {self.test_name}",
            "=" * 60,
            f"Total Assignments: {len(self.assignments)}",
            ""
        ]
        
        for variant_name, data in results.items():
            is_winner = variant_name == winner
            is_control = variant_name == self.control_variant
            
            marker = "🏆 " if is_winner else "📊 "
            control_marker = " (CONTROL)" if is_control else ""
            
            lines.extend([
                f"{marker}Variant: {variant_name}{control_marker}",
                f"  Assigned: {self.variant_counts.get(variant_name, 0)}",
                f"  Sent: {data['sent']} ({data['send_rate']*100:.1f}%)",
                f"  Failed: {data['failed']}",
                f"  Open Rate: {data['open_rate']*100:.1f}%",
                f"  Click Rate: {data['click_rate']*100:.1f}%",
                f"  Conversion Rate: {data['conversion_rate']*100:.1f}%",
                ""
            ])
        
        if winner:
            lines.append(f"Winner: {winner}")
        
        return "\n".join(lines)

