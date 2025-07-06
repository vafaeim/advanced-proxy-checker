# src/core/checker.py
"""
Core components for proxy validation, including latency measurement and
geolocation.
"""

import socket
import statistics
import json
import requests
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass
from time import perf_counter
from typing import Optional, List, Dict

# --- Constants ---
GEO_API_URL = "http://ip-api.com/json/{ip}?fields=status,country,countryCode"

# --- Data Structures ---

@dataclass
class Proxy:
    """
    Represents a proxy server and its associated metrics.
    
    Attributes:
        server: The server address (IP or hostname).
        port: The server port.
        secret: The proxy secret or password.
        original_url: The full original URL of the proxy.
        ping: The average latency in milliseconds.
        jitter: The standard deviation of latency in milliseconds.
        country_code: The two-letter ISO country code.
        country_name: The full name of the country.
    """
    server: str
    port: int
    secret: str
    original_url: str
    ping: Optional[int] = None
    jitter: Optional[float] = None
    country_code: Optional[str] = None
    country_name: Optional[str] = None

# --- Core Functions ---

def get_geo_info(ip_address: str) -> Dict[str, str]:
    """
    Fetches geographic information for a given IP address using ip-api.com.

    Args:
        ip_address: The IP address to geolocate.

    Returns:
        A dictionary containing the 'code' (country code) and 'name'
        (country name), or 'N/A' if lookup fails.
    """
    try:
        response = requests.get(GEO_API_URL.format(ip=ip_address), timeout=2)
        response.raise_for_status()
        data = response.json()
        if data.get('status') == 'success':
            return {
                "code": data.get('countryCode', 'N/A'),
                "name": data.get('country', 'N/A')
            }
    except (requests.RequestException, json.JSONDecodeError):
        # Fails silently to prevent a single API failure from halting the scan.
        pass
    return {"code": "N/A", "name": "N/A"}

def measure_latency(server: str, port: int, timeout: int) -> Optional[int]:
    """
    Measures a single TCP connection latency.

    Args:
        server: The server hostname or IP address.
        port: The server port.
        timeout: The connection timeout in seconds.

    Returns:
        The latency in milliseconds, or None if the connection fails.
    """
    try:
        start_time = perf_counter()
        with socket.create_connection((server, port), timeout=timeout):
            end_time = perf_counter()
        return int((end_time - start_time) * 1000)
    except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
        return None

def check_proxy(proxy: Proxy, count: int, timeout: int, fetch_country: bool) -> Optional[Proxy]:
    """
    Performs latency measurements and optionally fetches geographic data for a proxy.

    Args:
        proxy: The Proxy object to check.
        count: The number of latency measurements to perform.
        timeout: The connection timeout for each measurement.
        fetch_country: A boolean indicating whether to fetch geo-information.

    Returns:
        The updated Proxy object with metrics if successful, otherwise None.
    """
    latencies = [
        latency for _ in range(count)
        if (latency := measure_latency(proxy.server, proxy.port, timeout)) is not None
    ]

    if not latencies:
        return None

    proxy.ping = int(statistics.mean(latencies))
    proxy.jitter = round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 2)
    
    if fetch_country:
        try:
            ip_address = socket.gethostbyname(proxy.server)
            geo_info = get_geo_info(ip_address)
            proxy.country_code = geo_info["code"]
            proxy.country_name = geo_info["name"]
        except socket.gaierror:
            proxy.country_code = "N/A"
            proxy.country_name = "Lookup Failed"
            
    return proxy

def parse_proxy_url(proxy_url: str) -> Optional[Proxy]:
    """
    Parses a proxy URL string into a Proxy object.

    Args:
        proxy_url: The raw proxy URL string.

    Returns:
        A Proxy object if parsing is successful, otherwise None.
    """
    try:
        cleaned_url = proxy_url.strip()
        if not cleaned_url:
            return None
            
        query_params = parse_qs(urlparse(cleaned_url).query)
        server = query_params.get('server', [None])[0]
        port_str = query_params.get('port', [None])[0]
        secret = query_params.get('secret', [None])[0]

        if not all([server, port_str, secret]):
            return None
        
        return Proxy(
            server=server,
            port=int(port_str),
            secret=secret,
            original_url=cleaned_url
        )
    except (ValueError, IndexError, AttributeError):
        return None
