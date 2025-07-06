# src/core/checker.py
"""
Core components for proxy validation, including latency measurement,
anonymity checking, geolocation, and result filtering.
"""

import socket
import statistics
import json
import requests
import socks
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass, field
from time import perf_counter
from typing import Optional, List, Dict, Any

# --- Constants ---
GEO_API_URL = "http://ip-api.com/json/{ip}?fields=status,country,countryCode"
ANONYMITY_CHECK_URL = "http://httpbin.org/get"

# --- Data Structures ---

@dataclass
class Proxy:
    """Represents a proxy server and its associated metrics."""
    server: str
    port: int
    secret: str
    original_url: str
    ping: Optional[int] = None
    jitter: Optional[float] = None
    country_code: Optional[str] = None
    anonymity: str = "Unknown"
    ping_results: Dict[str, Optional[int]] = field(default_factory=dict)

@dataclass
class FilterCriteria:
    """Holds all filtering and sorting parameters."""
    max_ping: Optional[int] = None
    min_ping: Optional[int] = None
    include_countries: Optional[List[str]] = None
    exclude_countries: Optional[List[str]] = None
    require_secret: Optional[str] = None
    top_n: Optional[int] = None
    sort_by: str = 'ping'
    sort_order: str = 'asc'

# --- Core Functions ---

def get_geo_info(ip_address: str) -> Dict[str, str]:
    """Fetches geographic information for a given IP address."""
    try:
        response = requests.get(GEO_API_URL.format(ip=ip_address), timeout=3)
        response.raise_for_status()
        data = response.json()
        return {"code": data.get('countryCode', 'N/A')} if data.get('status') == 'success' else {"code": "N/A"}
    except requests.RequestException:
        return {"code": "N/A"}

def check_anonymity(proxy_server: str, proxy_port: int, timeout: int) -> str:
    """Checks the anonymity level of a SOCKS5 proxy."""
    proxies = {
        'http': f'socks5://{proxy_server}:{proxy_port}',
        'https': f'socks5://{proxy_server}:{proxy_port}'
    }
    try:
        response = requests.get(ANONYMITY_CHECK_URL, proxies=proxies, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        origin_ip = data.get('origin', '').split(', ')
        headers = data.get('headers', {})
        
        via = headers.get('Via', '')
        forwarded = headers.get('X-Forwarded-For', '')

        if len(origin_ip) > 1 or via or forwarded:
            return "Transparent"
        return "Elite"
    except (requests.RequestException, json.JSONDecodeError):
        return "Anonymous" # Can't confirm elite status, but it works

def measure_latency(server: str, port: int, timeout: int) -> Optional[int]:
    """Measures a single direct TCP connection latency."""
    try:
        start_time = perf_counter()
        with socket.create_connection((server, port), timeout=timeout):
            return int((perf_counter() - start_time) * 1000)
    except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
        return None

def measure_latency_via_proxy(proxy_server: str, proxy_port: int, target_server: str, target_port: int, timeout: int) -> Optional[int]:
    """Measures a single TCP connection latency to a target through a SOCKS5 proxy."""
    s = socks.socksocket()
    try:
        s.set_proxy(socks.SOCKS5, proxy_server, proxy_port)
        s.settimeout(timeout)
        start_time = perf_counter()
        s.connect((target_server, target_port))
        return int((perf_counter() - start_time) * 1000)
    except (socks.SOCKS5Error, socks.ProxyConnectionError, socket.timeout, socket.gaierror, OSError):
        return None
    finally:
        s.close()

def check_proxy(proxy: Proxy, count: int, timeout: int, fetch_country: bool, external_domains: List[str]) -> Optional[Proxy]:
    """Performs all checks for a single proxy."""
    latencies = [lat for _ in range(count) if (lat := measure_latency(proxy.server, proxy.port, timeout)) is not None]
    if not latencies: return None

    proxy.ping = int(statistics.mean(latencies))
    proxy.jitter = round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 2)
    
    proxy.anonymity = check_anonymity(proxy.server, proxy.port, timeout)

    if fetch_country:
        try:
            ip_address = socket.gethostbyname(proxy.server)
            proxy.country_code = get_geo_info(ip_address)["code"]
        except socket.gaierror:
            proxy.country_code = "N/A"
    
    for domain in external_domains:
        proxy.ping_results[domain] = measure_latency_via_proxy(proxy.server, proxy.port, domain, 443, timeout)

    return proxy

def parse_proxy_url(proxy_url: str) -> Optional[Proxy]:
    """Parses a proxy URL string into a Proxy object."""
    try:
        cleaned_url = proxy_url.strip()
        if not cleaned_url: return None
        query_params = parse_qs(urlparse(cleaned_url).query)
        server = query_params.get('server', [None])[0]
        port_str = query_params.get('port', [None])[0]
        secret = query_params.get('secret', [None])[0]
        if not all([server, port_str, secret]): return None
        return Proxy(server=server, port=int(port_str), secret=secret, original_url=cleaned_url)
    except (ValueError, IndexError, AttributeError):
        return None

def filter_and_sort_proxies(proxies: List[Proxy], criteria: FilterCriteria) -> List[Proxy]:
    """Applies a set of filters and sorting to a list of proxies."""
    filtered = proxies
    if criteria.max_ping is not None:
        filtered = [p for p in filtered if p.ping is not None and p.ping <= criteria.max_ping]
    if criteria.min_ping is not None:
        filtered = [p for p in filtered if p.ping is not None and p.ping >= criteria.min_ping]
    if criteria.require_secret:
        filtered = [p for p in filtered if criteria.require_secret in p.secret]
    if criteria.include_countries:
        codes = {c.upper() for c in criteria.include_countries}
        filtered = [p for p in filtered if p.country_code in codes]
    if criteria.exclude_countries:
        codes = {c.upper() for c in criteria.exclude_countries}
        filtered = [p for p in filtered if p.country_code not in codes]
    
    filtered.sort(key=lambda p: getattr(p, criteria.sort_by) or float('inf'), reverse=(criteria.sort_order == 'desc'))
    
    if criteria.top_n is not None:
        filtered = filtered[:criteria.top_n]
        
    return filtered
