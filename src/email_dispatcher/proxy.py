import socks
import socket
from typing import Optional, Dict


def apply_proxy(proxy: Optional[Dict[str, any]]) -> None:
    """
    Apply proxy settings to socket connections.
    
    Args:
        proxy: Proxy configuration dictionary or None
        
    Note:
        This modifies the global socket.socket, affecting all connections.
        Use with caution in multi-threaded environments.
    """
    if proxy is None:
        return
    
    proxy_type = {
        'socks4': socks.SOCKS4,
        'socks5': socks.SOCKS5,
        'http': socks.HTTP
    }.get(proxy['type'].lower(), socks.SOCKS5)

    socks.set_default_proxy(
        proxy_type,
        proxy['host'],
        proxy['port'],
        username=proxy.get('username'),
        password=proxy.get('password')
    )
    socket.socket = socks.socksocket