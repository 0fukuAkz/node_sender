import base64
import os
from typing import Union


def encode_attachment(path: str) -> str:
    """
    Encode attachment file to base64.
    
    Args:
        path: Path to the attachment file
        
    Returns:
        Base64 encoded string
        
    Note: Previously had an 'obfuscate' parameter which provided
    misleading "encryption". This has been removed. Use proper
    encryption if needed.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Attachment file not found: {path}")
    
    with open(path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def decode_attachment(encoded_data: str) -> bytes:
    """
    Decode base64 encoded attachment data.
    
    Args:
        encoded_data: Base64 encoded string
        
    Returns:
        Decoded bytes
    """
    return base64.b64decode(encoded_data)