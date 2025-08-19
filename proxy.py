import socks
import socket

def apply_proxy(proxy):
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