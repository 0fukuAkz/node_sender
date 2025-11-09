"""
SMTP connection pooling for high-performance email sending
"""

import smtplib
import ssl
import threading
import time
from typing import Optional, Dict
from queue import Queue, Empty
from .exceptions import SMTPConnectionError, SMTPAuthenticationError


class SMTPConnection:
    """Wrapper for SMTP connection with health tracking."""
    
    def __init__(self, smtp_settings: Dict[str, any]):
        """
        Initialize SMTP connection.
        
        Args:
            smtp_settings: Dictionary with SMTP configuration
        """
        self.smtp_settings = smtp_settings
        self.connection: Optional[smtplib.SMTP] = None
        self.ssl_connection: Optional[smtplib.SMTP_SSL] = None
        self.created_at = time.monotonic()
        self.last_used = time.monotonic()
        self.use_count = 0
        self.is_healthy = True
        self.lock = threading.Lock()
    
    def connect(self) -> None:
        """
        Establish SMTP connection.
        
        Raises:
            SMTPConnectionError: If connection fails
            SMTPAuthenticationError: If authentication fails
        """
        try:
            context = ssl.create_default_context()
            host = self.smtp_settings['host']
            port = self.smtp_settings['port']
            
            if port == 465:
                # SSL connection
                self.ssl_connection = smtplib.SMTP_SSL(host, port, context=context)
                server = self.ssl_connection
            else:
                # TLS connection
                self.connection = smtplib.SMTP(host, port)
                server = self.connection
                if self.smtp_settings.get('use_tls', True):
                    server.starttls(context=context)
            
            # Authenticate
            if self.smtp_settings.get('use_auth', True):
                username = self.smtp_settings['username']
                password = self.smtp_settings['password']
                try:
                    server.login(username, password)
                except smtplib.SMTPAuthenticationError as e:
                    self.close()
                    raise SMTPAuthenticationError(f"SMTP authentication failed: {e}")
            
            self.is_healthy = True
            
        except smtplib.SMTPException as e:
            self.is_healthy = False
            raise SMTPConnectionError(f"Failed to connect to SMTP server: {e}")
        except Exception as e:
            self.is_healthy = False
            raise SMTPConnectionError(f"Unexpected error connecting to SMTP: {e}")
    
    def send_message(self, msg) -> None:
        """
        Send email message.
        
        Args:
            msg: EmailMessage object to send
            
        Raises:
            SMTPConnectionError: If sending fails
        """
        with self.lock:
            try:
                server = self.ssl_connection if self.ssl_connection else self.connection
                if server is None:
                    raise SMTPConnectionError("Not connected")
                
                server.send_message(msg)
                self.last_used = time.monotonic()
                self.use_count += 1
                
            except (smtplib.SMTPServerDisconnected, smtplib.SMTPException) as e:
                self.is_healthy = False
                raise SMTPConnectionError(f"Failed to send message: {e}")
    
    def close(self) -> None:
        """Close SMTP connection."""
        with self.lock:
            try:
                if self.ssl_connection:
                    self.ssl_connection.quit()
                elif self.connection:
                    self.connection.quit()
            except Exception:
                pass  # Ignore errors on close
            finally:
                self.ssl_connection = None
                self.connection = None
                self.is_healthy = False
    
    def health_check(self) -> bool:
        """
        Check if connection is still healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        with self.lock:
            if not self.is_healthy:
                return False
            
            server = self.ssl_connection if self.ssl_connection else self.connection
            if server is None:
                return False
            
            try:
                # Send NOOP to check connection
                status = server.noop()
                return status[0] == 250
            except Exception:
                self.is_healthy = False
                return False
    
    def get_age(self) -> float:
        """Get connection age in seconds."""
        return time.monotonic() - self.created_at
    
    def get_idle_time(self) -> float:
        """Get time since last use in seconds."""
        return time.monotonic() - self.last_used


class SMTPConnectionPool:
    """
    Thread-safe SMTP connection pool for high-performance email sending.
    """
    
    def __init__(
        self,
        smtp_settings: Dict[str, any],
        pool_size: int = 5,
        max_age: float = 300.0,
        max_idle: float = 60.0,
        max_uses: int = 100
    ):
        """
        Initialize connection pool.
        
        Args:
            smtp_settings: SMTP configuration dictionary
            pool_size: Maximum number of connections in pool
            max_age: Maximum connection age in seconds (0 = unlimited)
            max_idle: Maximum idle time before closing (0 = unlimited)
            max_uses: Maximum uses per connection (0 = unlimited)
        """
        self.smtp_settings = smtp_settings
        self.pool_size = pool_size
        self.max_age = max_age
        self.max_idle = max_idle
        self.max_uses = max_uses
        
        self.pool: Queue = Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.created_count = 0
        self.total_created = 0
        self.total_destroyed = 0
        
        # Statistics
        self.stats = {
            'total_gets': 0,
            'total_puts': 0,
            'total_created': 0,
            'total_reused': 0,
            'total_destroyed': 0,
            'health_check_failures': 0,
        }
        self.stats_lock = threading.Lock()
    
    def _create_connection(self) -> SMTPConnection:
        """
        Create new SMTP connection.
        
        Returns:
            New SMTPConnection instance
            
        Raises:
            SMTPConnectionError: If connection creation fails
        """
        conn = SMTPConnection(self.smtp_settings)
        conn.connect()
        
        with self.lock:
            self.created_count += 1
            self.total_created += 1
        
        with self.stats_lock:
            self.stats['total_created'] += 1
        
        return conn
    
    def _should_recreate(self, conn: SMTPConnection) -> bool:
        """
        Check if connection should be recreated.
        
        Args:
            conn: Connection to check
            
        Returns:
            True if should recreate, False otherwise
        """
        # Check age
        if self.max_age > 0 and conn.get_age() > self.max_age:
            return True
        
        # Check idle time
        if self.max_idle > 0 and conn.get_idle_time() > self.max_idle:
            return True
        
        # Check use count
        if self.max_uses > 0 and conn.use_count >= self.max_uses:
            return True
        
        # Health check
        if not conn.health_check():
            with self.stats_lock:
                self.stats['health_check_failures'] += 1
            return True
        
        return False
    
    def get_connection(self, timeout: float = 5.0) -> SMTPConnection:
        """
        Get connection from pool.
        
        Args:
            timeout: Maximum time to wait for connection
            
        Returns:
            SMTPConnection instance
            
        Raises:
            SMTPConnectionError: If cannot get connection
        """
        with self.stats_lock:
            self.stats['total_gets'] += 1
        
        # Try to get existing connection from pool
        try:
            conn = self.pool.get(block=True, timeout=timeout)
            
            # Check if connection should be recreated
            if self._should_recreate(conn):
                conn.close()
                with self.lock:
                    self.created_count -= 1
                    self.total_destroyed += 1
                with self.stats_lock:
                    self.stats['total_destroyed'] += 1
                
                # Create new connection
                conn = self._create_connection()
            else:
                with self.stats_lock:
                    self.stats['total_reused'] += 1
            
            return conn
            
        except Empty:
            # No connection available, create new one if under limit
            with self.lock:
                if self.created_count < self.pool_size:
                    return self._create_connection()
            
            # Pool is full and no connections available
            raise SMTPConnectionError(
                f"Connection pool exhausted (timeout={timeout}s)"
            )
    
    def return_connection(self, conn: SMTPConnection) -> None:
        """
        Return connection to pool.
        
        Args:
            conn: Connection to return
        """
        with self.stats_lock:
            self.stats['total_puts'] += 1
        
        # Check if connection is still healthy
        if not conn.is_healthy or self._should_recreate(conn):
            conn.close()
            with self.lock:
                self.created_count -= 1
                self.total_destroyed += 1
            with self.stats_lock:
                self.stats['total_destroyed'] += 1
            return
        
        # Return to pool
        try:
            self.pool.put_nowait(conn)
        except Exception:
            # Pool is full, close connection
            conn.close()
            with self.lock:
                self.created_count -= 1
                self.total_destroyed += 1
            with self.stats_lock:
                self.stats['total_destroyed'] += 1
    
    def close_all(self) -> None:
        """Close all connections in pool."""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
                with self.lock:
                    self.created_count -= 1
                    self.total_destroyed += 1
            except Empty:
                break
    
    def get_stats(self) -> Dict[str, any]:
        """
        Get pool statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self.stats_lock:
            stats = self.stats.copy()
        
        with self.lock:
            stats['current_size'] = self.created_count
            stats['max_size'] = self.pool_size
            stats['available'] = self.pool.qsize()
        
        return stats


class ConnectionPoolContextManager:
    """Context manager for connection pool usage."""
    
    def __init__(self, pool: SMTPConnectionPool, timeout: float = 5.0):
        """
        Initialize context manager.
        
        Args:
            pool: Connection pool to use
            timeout: Timeout for getting connection
        """
        self.pool = pool
        self.timeout = timeout
        self.connection: Optional[SMTPConnection] = None
    
    def __enter__(self) -> SMTPConnection:
        """Get connection from pool."""
        self.connection = self.pool.get_connection(self.timeout)
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Return connection to pool."""
        if self.connection:
            if exc_type is not None:
                # Exception occurred, mark connection as unhealthy
                self.connection.is_healthy = False
            self.pool.return_connection(self.connection)
        return False

