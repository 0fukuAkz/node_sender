"""
Unit tests for file I/O operations
"""

import pytest
import os
import tempfile
from src.email_dispatcher.file_io import read_lines, read_lines_chunked, log_line, clear_file, file_exists


class TestFileIO:
    """Test file I/O operations."""
    
    @pytest.fixture
    def temp_file(self):
        """Create temporary file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("line1\nline2\n\nline3\n")
            temp_path = f.name
        
        yield temp_path
        
        try:
            os.unlink(temp_path)
        except:
            pass
    
    def test_read_lines(self, temp_file):
        """Test reading lines from file."""
        lines = read_lines(temp_file)
        
        assert len(lines) == 3  # Empty lines excluded
        assert lines[0] == 'line1'
        assert lines[1] == 'line2'
        assert lines[2] == 'line3'
    
    def test_read_lines_chunked(self, temp_file):
        """Test reading lines in chunks."""
        chunks = list(read_lines_chunked(temp_file, chunk_size=2))
        
        assert len(chunks) == 2
        assert len(chunks[0]) == 2
        assert len(chunks[1]) == 1
    
    def test_log_line(self, tmp_path):
        """Test appending line to file."""
        log_file = tmp_path / 'test.log'
        
        log_line(str(log_file), 'Log entry 1')
        log_line(str(log_file), 'Log entry 2')
        
        lines = read_lines(str(log_file))
        assert len(lines) == 2
        assert lines[0] == 'Log entry 1'
        assert lines[1] == 'Log entry 2'
    
    def test_clear_file(self, temp_file):
        """Test clearing file contents."""
        clear_file(temp_file)
        
        lines = read_lines(temp_file)
        assert len(lines) == 0
    
    def test_file_exists_true(self, temp_file):
        """Test file_exists for existing file."""
        assert file_exists(temp_file) is True
    
    def test_file_exists_false(self):
        """Test file_exists for non-existent file."""
        assert file_exists('nonexistent_file.txt') is False
    
    def test_log_line_creates_directory(self, tmp_path):
        """Test that log_line creates directory if needed."""
        log_file = tmp_path / 'subdir' / 'test.log'
        
        log_line(str(log_file), 'Test entry')
        
        assert log_file.exists()
        assert log_file.parent.exists()

