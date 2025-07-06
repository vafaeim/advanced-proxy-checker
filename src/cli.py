#!/usr/bin/env python3
# src/cli.py
"""
Command-Line Interface for the Advanced Proxy Latency Checker.
"""

import argparse
import csv
import json
import os
import sys
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from typing import List, TextIO

from core.checker import Proxy, check_proxy, parse_proxy_url
try:
    from tqdm import tqdm
except ImportError:
    print("Error: 'tqdm' is not installed. Please run 'pip install tqdm'.", file=sys.stderr)
    sys.exit(1)

__author__ = "Amirreza Vafaei Moghadam"
__version__ = "5.0.0"
__license__ = "MIT"
__copyright__ = f"Copyright 2025, {__author__}"

DEFAULT_TIMEOUT = 2
DEFAULT_WORKERS = 50
DEFAULT_PING_COUNT = 3
DEFAULT_PROXY_FILE = "update_proxies.txt"

def get_proxies_from_source(args: argparse.Namespace) -> List[Proxy]:
    """Reads and parses proxy URLs from the specified source."""
    urls = set()
    source_name = ""
    try:
        if args.stdin:
            source_name = "standard input"
            urls = {line.strip() for line in sys.stdin if line.strip()}
        elif args.url:
            source_name = f"URL '{args.url}'"
            response = requests.get(args.url, timeout=10)
            response.raise_for_status()
            urls = {line.strip() for line in response.text.splitlines() if line.strip()}
        else:
            source_name = f"file '{args.file_path}'"
            with open(args.file_path, 'r', encoding='utf-8') as f:
                urls = {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        print(f"Error: Input file not found at '{args.file_path}'", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Error fetching proxies from URL: {e}", file=sys.stderr)
        sys.exit(1)
    
    parsed_proxies = [p for p in (parse_proxy_url(url) for url in urls) if p]
    if not parsed_proxies:
        print(f"Warning: No valid proxy URLs were found in {source_name}.", file=sys.stderr)
    return parsed_proxies

def save_results(proxies: List[Proxy], output_file: TextIO, format_type: str, external_domains: List[str]):
    """Saves the list of proxies to the given file."""
    if format_type == 'json':
        json.dump([asdict(p) for p in proxies], output_file, indent=2)
    elif format_type == 'csv':
        headers = ['ping', 'jitter', 'server', 'port', 'country_code', 'url'] + [f'ping_{d}' for d in external_domains]
        writer = csv.writer(output_file)
        writer.writerow(headers)
        for p in proxies:
            row = [p.ping, p.jitter, p.server, p.port, p.country_code, p.original_url]
            row.extend([p.ping_results.get(d) for d in external_domains])
            writer.writerow(row)
    else:
        for proxy in proxies:
            output_file.write(f"{proxy.original_url}\n")

def print_results_table(proxies: List[Proxy], show_country: bool, external_domains: List[str]):
    """Prints the final results in a formatted table."""
    if not proxies:
        return
        
    print(f"\n--- Analysis Complete: {len(proxies)} Proxies Matched Criteria ---")
    
    headers = [('Ping (ms)', 10), ('Jitter', 8), ('Server', 25), ('Port', 6)]
    if show_country:
        headers.append(('Country', 10))
    for domain in external_domains:
        headers.append((f'Ping {domain[:10]}', 15))

    try:
        max_server_len = max(len(p.server) for p in proxies)
        headers[2] = ('Server', max(max_server_len, len("Server")) + 2)
    except (ValueError, IndexError):
        pass

    header_line = "".join([f"{h[0]:<{h[1]}}" for h in headers])
    print(header_line)
    print("".join([f"{'-'*(h[1]-1):<{h[1]}}" for h in headers]))

    for p in proxies:
        row_items = [
            f"{p.ping:<{headers[0][1]}}",
            f"{p.jitter:<{headers[1][1]}.2f}",
            f"{p.server:<{headers[2][1]}}",
            f"{p.port:<{headers[3][1]}}",
        ]
        if show_country:
            row_items.append(f"{p.country_code or 'N/A':<{headers[4][1]}}")
        for i, domain in enumerate(external_domains):
            ping_val = p.ping_results.get(domain)
            ping_str = str(ping_val) if ping_val is not None else 'N/A'
            row_items.append(f"{ping_str:<{headers[5+i][1]}}")
        print("".join(row_items))

def main():
    """Parses arguments and orchestrates the proxy checking process."""
    parser = argparse.ArgumentParser(
        description=f"Advanced Proxy Latency Checker (v{__version__}) by {__author__}.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"Example: python src/cli.py --top 10 -o healthy.txt --ping-to google.com"
    )
    
    input_group = parser.add_argument_group('Input Source')
    filter_group = parser.add_argument_group('Filtering & Sorting')
    output_group = parser.add_argument_group('Output Configuration')
    conn_group = parser.add_argument_group('Connection Settings')
    
    source_exclusive_group = input_group.add_mutually_exclusive_group()
    source_exclusive_group.add_argument("file_path", nargs='?', help=f"Path to a file with proxy URLs. Defaults to '{DEFAULT_PROXY_FILE}' if present.")
    source_exclusive_group.add_argument("--url", help="URL to fetch a list of proxy URLs from.")
    source_exclusive_group.add_argument("--stdin", action='store_true', help="Read proxy URLs from standard input.")

    filter_group.add_argument("--top", type=int, metavar='N', help="Limit output to the top N fastest proxies.")
    filter_group.add_argument("--max-ping", type=int, metavar='MS', help="Exclude proxies with latency greater than MS.")
    filter_group.add_argument("--min-ping", type=int, metavar='MS', help="Exclude proxies with latency less than MS.")
    filter_group.add_argument("--country", nargs='+', metavar='CC', help="Include only specified ISO country codes (e.g., US JP).")
    filter_group.add_argument("--exclude-country", nargs='+', metavar='CC', help="Exclude specified ISO country codes.")
    filter_group.add_argument("--require-secret", type=str, metavar='PATTERN', help="Only include proxies where the secret contains this pattern.")
    filter_group.add_argument("--sort-by", choices=['ping', 'jitter'], default='ping', help="Sort results by 'ping' or 'jitter'. (default: ping)")
    filter_group.add_argument("--sort-order", choices=['asc', 'desc'], default='asc', help="Sort order: 'asc' or 'desc'. (default: asc)")
    
    output_group.add_argument("-o", "--output", type=argparse.FileType('w', encoding='UTF-8'), help="Path to save the results. If not provided, prints to console.")
    output_format_group = output_group.add_mutually_exclusive_group()
    output_format_group.add_argument("--csv", action='store_const', const='csv', dest='format', help="Set output format to CSV.")
    output_format_group.add_argument("--json", action='store_const', const='json', dest='format', help="Set output format to JSON.")
    output_group.add_argument("--silent", action='store_true', help="Suppress all console output except for fatal errors.")
    
    conn_group.add_argument("--ping-to", nargs='+', metavar='DOMAIN', default=[], help="List of external domains to ping through the proxy (e.g., google.com).")
    conn_group.add_argument("-c", "--count", type=int, default=DEFAULT_PING_COUNT, help=f"Pings per proxy for averaging. (default: {DEFAULT_PING_COUNT})")
    conn_group.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"Connection timeout in seconds. (default: {DEFAULT_TIMEOUT})")
    conn_group.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS, help=f"Number of concurrent workers. (default: {DEFAULT_WORKERS})")
    
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    
    args = parser.parse_args()
    log = lambda message: print(message, file=sys.stderr) if not args.silent else None

    if not args.file_path and not args.url and not args.stdin:
        if os.path.exists(DEFAULT_PROXY_FILE):
            args.file_path = DEFAULT_PROXY_FILE
            log(f"No input source specified. Defaulting to '{DEFAULT_PROXY_FILE}'.")
        else:
            parser.error(f"No input source specified. Please provide a file path, --url, --stdin, or ensure '{DEFAULT_PROXY_FILE}' exists.")

    proxies_to_check = get_proxies_from_source(args)
    if not proxies_to_check:
        sys.exit(1)

    log(f"Found {len(proxies_to_check)} unique proxies. Commencing checks...")

    fetch_country = bool(args.country) or bool(args.exclude_country)
    healthy_proxies: List[Proxy] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(check_proxy, p, args.count, args.timeout, fetch_country, args.ping_to) for p in proxies_to_check}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Processing", unit="proxy", disable=args.silent):
            if result := future.result():
                healthy_proxies.append(result)

    # --- Filtering and Sorting ---
    if args.max_ping is not None:
        healthy_proxies = [p for p in healthy_proxies if p.ping is not None and p.ping <= args.max_ping]
    if args.min_ping is not None:
        healthy_proxies = [p for p in healthy_proxies if p.ping is not None and p.ping >= args.min_ping]
    if args.require_secret:
        healthy_proxies = [p for p in healthy_proxies if args.require_secret in p.secret]
    if args.country:
        codes = {c.upper() for c in args.country}
        healthy_proxies = [p for p in healthy_proxies if p.country_code in codes]
    if args.exclude_country:
        codes = {c.upper() for c in args.exclude_country}
        healthy_proxies = [p for p in healthy_proxies if p.country_code not in codes]
    
    healthy_proxies.sort(key=lambda p: getattr(p, args.sort_by) or float('inf'), reverse=(args.sort_order == 'desc'))
    if args.top is not None:
        healthy_proxies = healthy_proxies[:args.top]

    # --- Output ---
    if args.output:
        save_results(healthy_proxies, args.output, args.format or 'txt', args.ping_to)
        log(f"Results successfully saved to '{args.output.name}'.")
    elif not args.silent:
        print_results_table(healthy_proxies, fetch_country, args.ping_to)

if __name__ == "__main__":
    main()
