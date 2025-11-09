from typing import List, Iterator, Optional
import os


def read_lines(path: str) -> List[str]:
    """
    Read all non-empty lines from file.
    
    Args:
        path: Path to file
        
    Returns:
        List of stripped lines
    """
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def read_lines_chunked(path: str, chunk_size: int = 1000) -> Iterator[List[str]]:
    """
    Read lines from file in chunks for memory efficiency.
    
    Args:
        path: Path to file
        chunk_size: Number of lines per chunk
        
    Yields:
        Chunks of lines
    """
    chunk = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                chunk.append(line)
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
        
        # Yield remaining lines
        if chunk:
            yield chunk


def log_line(path: str, content: str) -> None:
    """
    Append line to file.
    
    Args:
        path: Path to file
        content: Content to append
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    
    with open(path, 'a', encoding='utf-8') as f:
        f.write(content + '\n')


def clear_file(path: str) -> None:
    """
    Clear file contents (create if doesn't exist).
    
    Args:
        path: Path to file
    """
    # Ensure directory exists
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    
    open(path, 'w').close()


def file_exists(path: str) -> bool:
    """
    Check if file exists.
    
    Args:
        path: Path to file
        
    Returns:
        True if file exists
    """
    return os.path.exists(path) and os.path.isfile(path)