"""
Unit tests for template processing
"""

import pytest
import tempfile
import os
from src.email_dispatcher.template import load_template, apply_placeholders, validate_path
from src.email_dispatcher.exceptions import PathSecurityError, TemplateError


class TestTemplate:
    """Test template processing."""
    
    @pytest.fixture
    def temp_template(self):
        """Create temporary template file."""
        os.makedirs('templates', exist_ok=True)
        content = """
<html>
<body>
<h1>Hello {recipient}!</h1>
<p>From {company}</p>
<p>{message}</p>
</body>
</html>
"""
        
        with open('templates/test_template.html', 'w') as f:
            f.write(content)
        
        yield 'templates/test_template.html'
        
        # Cleanup
        try:
            os.unlink('templates/test_template.html')
        except:
            pass
    
    def test_load_template(self, temp_template):
        """Test loading template file."""
        content = load_template(temp_template)
        assert 'Hello {recipient}!' in content
        assert '{company}' in content
    
    def test_apply_placeholders(self):
        """Test placeholder substitution."""
        template = "Hello {name}, welcome to {company}!"
        placeholders = {
            'name': 'John',
            'company': 'Acme Corp'
        }
        
        result = apply_placeholders(template, placeholders)
        assert result == "Hello John, welcome to Acme Corp!"
    
    def test_apply_placeholders_partial(self):
        """Test placeholder substitution with missing values."""
        template = "Hello {name}, your ID is {id}!"
        placeholders = {'name': 'John'}
        
        result = apply_placeholders(template, placeholders)
        assert 'John' in result
        assert '{id}' in result  # Unmapped placeholders remain
    
    def test_validate_path_success(self, temp_template):
        """Test successful path validation."""
        path = validate_path(temp_template)
        assert path.exists()
    
    def test_validate_path_nonexistent(self):
        """Test validation fails for nonexistent file."""
        with pytest.raises(PathSecurityError):
            validate_path('templates/nonexistent.html')
    
    def test_validate_path_traversal(self):
        """Test validation catches path traversal."""
        with pytest.raises(PathSecurityError):
            validate_path('../../../etc/passwd')
    
    def test_validate_path_outside_allowed_dirs(self):
        """Test validation rejects paths outside allowed directories."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            temp_file = f.name
        
        try:
            with pytest.raises(PathSecurityError):
                validate_path(temp_file)
        finally:
            os.unlink(temp_file)

