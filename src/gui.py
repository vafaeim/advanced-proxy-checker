#!/usr/bin/env python3
# src/gui.py
"""
Graphical User Interface for the Advanced Proxy Latency Checker.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import threading
import queue
import csv
import json
import base64
import os
import ttkbootstrap as bst
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Dict
from collections import Counter

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.checker import Proxy, check_proxy, parse_proxy_url, FilterCriteria, filter_and_sort_proxies
from assets import APP_ICON_DATA

__author__ = "Amirreza Vafaei Moghadam"
__version__ = "7.0.1"
__license__ = "MIT"
__copyright__ = f"Copyright 2025, {__author__}"

DEFAULT_TIMEOUT = 2
DEFAULT_WORKERS = 50
DEFAULT_PING_COUNT = 3
URL_PLACEHOLDER = "https://raw.githubusercontent.com/vafaeim/advanced-proxy-checker/main/update_proxies.txt"
CONFIG_FILE = "config.json"

class ToolTip:
    """Creates a tooltip for a given widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, background="#3c3c3c", foreground="white", relief='solid', borderwidth=1, wraplength=200, justify='left')
        label.pack(ipadx=1)

    def hide(self, event=None):
        if self.tooltip: self.tooltip.destroy()
        self.tooltip = None

class ProxyCheckerGUI(bst.Window):
    """The main application window for the proxy checker GUI."""

    def __init__(self):
        super().__init__(themename="superhero")
        self.title(f"Advanced Proxy Latency Checker v{__version__}")
        
        self.proxies_to_check: List[Proxy] = []
        self.results: List[Proxy] = []
        self.result_queue = queue.Queue()
        self.scan_running = threading.Event()
        self.scan_paused = threading.Event()
        self.external_domains = []
        self.total_proxies = 0
        self.checked_proxies = 0
        self.healthy_proxies = 0

        self._load_config()
        self._load_icons()
        if self.app_icon: self.iconphoto(True, self.app_icon)

        self._create_menu()
        self._create_widgets()
        self.after(100, self._process_queue)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _load_config(self):
        """Loads user configuration from a JSON file."""
        try:
            with open(CONFIG_FILE, 'r') as f:
                self.app_config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.app_config = {}
        
        self.geometry(self.app_config.get("geometry", "1300x850"))
        
    def _save_config(self):
        """Saves current settings to the configuration file."""
        self.app_config["geometry"] = self.geometry()
        # Add other settings to save here
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.app_config, f, indent=2)

    def on_closing(self):
        """Handles window closing event."""
        self._save_config()
        self.destroy()

    def _load_icons(self):
        """Loads all icons from base64 data."""
        def load_image(data):
            if not data: return None
            try: return tk.PhotoImage(data=base64.b64decode(data))
            except tk.TclError: return None
        self.app_icon = load_image(APP_ICON_DATA)

    def _create_menu(self):
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="Save Results...", command=self._save_results, accelerator="Ctrl+S", state="disabled")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")
        menubar.add_cascade(label="File", menu=self.file_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self._show_about_dialog)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.bind_all("<Control-s>", lambda e: self._save_results())
        self.bind_all("<Control-q>", lambda e: self.on_closing())

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        controls_frame = ttk.Frame(paned_window, width=420)
        paned_window.add(controls_frame, weight=1)
        self._create_controls_pane(controls_frame)
        
        results_frame = ttk.Frame(paned_window)
        self._create_results_pane(results_frame)
        paned_window.add(results_frame, weight=3)
        
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Frame(main_frame)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        ttk.Label(status_bar, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)
        self.progress_text_var = tk.StringVar()
        ttk.Label(status_bar, textvariable=self.progress_text_var).pack(side=tk.RIGHT, padx=5)

    def _create_controls_pane(self, parent: ttk.Frame):
        parent.pack_propagate(False)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        self._create_action_buttons(parent)

        self.notebook = ttk.Notebook(parent, style='TNotebook')
        self.notebook.grid(row=1, column=0, sticky="nsew", pady=10)

        source_tab = ttk.Frame(self.notebook, padding=10)
        connection_tab = ttk.Frame(self.notebook, padding=10)
        filtering_tab = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(source_tab, text="Source")
        self.notebook.add(connection_tab, text="Connection")
        self.notebook.add(filtering_tab, text="Filtering & Sorting")

        self._create_source_tab(source_tab)
        self._create_connection_tab(connection_tab)
        self._create_filtering_tab(filtering_tab)

    def _create_action_buttons(self, parent: ttk.Frame):
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=0, sticky="ew")
        frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        self.start_button = ttk.Button(frame, text="Start Scan", command=self._start_scan, bootstyle="success")
        self.start_button.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        self.pause_button = ttk.Button(frame, text="Pause", command=self._pause_scan, state=tk.DISABLED, bootstyle="warning")
        self.pause_button.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.stop_button = ttk.Button(frame, text="Stop", command=self._stop_scan, state=tk.DISABLED, bootstyle="danger")
        self.stop_button.grid(row=0, column=2, sticky=tk.EW, padx=5)
        self.clear_button = ttk.Button(frame, text="Clear", command=self._clear_all, bootstyle="secondary")
        self.clear_button.grid(row=0, column=3, sticky=tk.EW, padx=(5, 0))

    def _create_source_tab(self, parent: ttk.Frame):
        self.input_source_var = tk.StringVar(value="url")
        radio_frame = ttk.Frame(parent)
        radio_frame.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(radio_frame, text="URL", variable=self.input_source_var, value="url", command=self._on_input_source_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(radio_frame, text="File", variable=self.input_source_var, value="file", command=self._on_input_source_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(radio_frame, text="Text", variable=self.input_source_var, value="text", command=self._on_input_source_change).pack(side=tk.LEFT, padx=5)
        
        self.url_entry = ttk.Entry(parent, font=("Helvetica", 10))
        self.url_entry.insert(0, self.app_config.get("last_url", URL_PLACEHOLDER))
        
        self.file_frame = ttk.Frame(parent)
        self.file_path_var = tk.StringVar(value=self.app_config.get("last_file", ""))
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path_var, state='readonly')
        self.file_button = ttk.Button(self.file_frame, text="Browse...", command=self._browse_file, bootstyle="info-outline")
        self.file_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 5))
        self.file_button.pack(side=tk.RIGHT)
        
        self.text_frame = ttk.Frame(parent)
        self.text_area = tk.Text(self.text_frame, height=10, undo=True, bg="#1c1c1c", fg="white", insertbackground="white", relief="solid", borderwidth=1)
        self.text_scroll = ttk.Scrollbar(self.text_frame, orient="vertical", command=self.text_area.yview)
        self.text_area['yscrollcommand'] = self.text_scroll.set
        self.text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._on_input_source_change()

    def _create_connection_tab(self, parent: ttk.Frame):
        parent.grid_columnconfigure(1, weight=1)
        def add_conn_row(label_text, var, row, default_val, tooltip_text):
            label = ttk.Label(parent, text=label_text)
            label.grid(row=row, column=0, sticky=tk.W, pady=8)
            var.set(self.app_config.get(var._name, default_val))
            entry = ttk.Spinbox(parent, from_=1, to=200, width=8, textvariable=var)
            entry.grid(row=row, column=1, sticky=tk.W, pady=8)
            ToolTip(label, tooltip_text)
        self.count_var = tk.IntVar(self, name="ping_count")
        add_conn_row("Ping Count:", self.count_var, 0, DEFAULT_PING_COUNT, "Number of pings per proxy for averaging.")
        self.timeout_var = tk.IntVar(self, name="timeout")
        add_conn_row("Timeout (s):", self.timeout_var, 1, DEFAULT_TIMEOUT, "Connection timeout in seconds for each ping.")
        self.workers_var = tk.IntVar(self, name="workers")
        add_conn_row("Workers:", self.workers_var, 2, DEFAULT_WORKERS, "Number of concurrent threads for checking proxies.")
        ping_label = ttk.Label(parent, text="Ping to Domains:")
        ping_label.grid(row=3, column=0, sticky=tk.W, pady=8)
        self.ping_to_var = tk.StringVar(self, name="ping_to_domains", value=self.app_config.get("ping_to_domains", "google.com, cloudflare.com"))
        ping_entry = ttk.Entry(parent, textvariable=self.ping_to_var)
        ping_entry.grid(row=3, column=1, sticky=tk.EW, pady=8)
        ToolTip(ping_label, "Comma-separated list of domains to ping through the proxies.")

    def _create_filtering_tab(self, parent: ttk.Frame):
        parent.grid_columnconfigure(1, weight=1)
        def add_filter_row(label_text, var, row, tooltip_text):
            label = ttk.Label(parent, text=label_text)
            label.grid(row=row, column=0, sticky=tk.W, pady=8)
            var.set(self.app_config.get(var._name, ""))
            entry = ttk.Entry(parent, textvariable=var)
            entry.grid(row=row, column=1, sticky=tk.EW, pady=8)
            ToolTip(label, tooltip_text)
        self.max_ping_var = tk.StringVar(self, name="max_ping")
        add_filter_row("Max Ping (ms):", self.max_ping_var, 0, "Exclude proxies with ping higher than this value.")
        self.min_ping_var = tk.StringVar(self, name="min_ping")
        add_filter_row("Min Ping (ms):", self.min_ping_var, 1, "Exclude proxies with ping lower than this value.")
        self.include_country_var = tk.StringVar(self, name="include_countries")
        add_filter_row("Include Countries:", self.include_country_var, 2, "Comma-separated list of country codes (e.g., US, DE).")
        self.exclude_country_var = tk.StringVar(self, name="exclude_countries")
        add_filter_row("Exclude Countries:", self.exclude_country_var, 3, "Comma-separated list of country codes (e.g., CN, RU).")
        self.secret_var = tk.StringVar(self, name="require_secret")
        add_filter_row("Require Secret:", self.secret_var, 4, "Only include proxies where the secret contains this text.")
        self.top_n_var = tk.StringVar(self, name="top_n")
        add_filter_row("Top N Results:", self.top_n_var, 5, "Limit the final output to the top N proxies.")
        self.show_country_var = tk.BooleanVar(self, name="show_country", value=self.app_config.get("show_country", True))
        cb = ttk.Checkbutton(parent, text="Fetch & Show Country", variable=self.show_country_var, bootstyle="primary-round-toggle")
        cb.grid(row=6, columnspan=2, sticky=tk.W, pady=10)
        ToolTip(cb, "Fetches country data for all proxies. Required for country filtering.")

    def _create_results_pane(self, parent: ttk.Frame):
        parent.rowconfigure(2, weight=1)
        parent.columnconfigure(0, weight=1)
        
        dash_frame = ttk.Frame(parent)
        dash_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        dash_frame.grid_columnconfigure((0,1,2), weight=1)
        self.total_var = tk.StringVar(value="Total: 0")
        self.healthy_var = tk.StringVar(value="Healthy: 0")
        self.failed_var = tk.StringVar(value="Failed: 0")
        ttk.Label(dash_frame, textvariable=self.total_var, font=("-size 12")).pack(side=tk.LEFT, expand=True)
        ttk.Label(dash_frame, textvariable=self.healthy_var, font=("-size 12")).pack(side=tk.LEFT, expand=True)
        ttk.Label(dash_frame, textvariable=self.failed_var, font=("-size 12")).pack(side=tk.LEFT, expand=True)

        self.progress_bar = ttk.Progressbar(parent, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10), columnspan=2)
        
        self.tree = ttk.Treeview(parent, show='headings', bootstyle="primary")
        self.tree_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview, bootstyle="round")
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree.grid(row=2, column=0, sticky="nsew")
        self.tree_scroll.grid(row=2, column=1, sticky="ns")
        
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2e2e2e", fg="white")
        self.context_menu.add_command(label="Copy URL", command=self._copy_url)
        self.context_menu.add_command(label="Copy Row", command=self._copy_row)
        self.tree.bind("<Button-3>", self._show_context_menu)
        self.tree.bind("<Double-1>", self._show_details_window)
        self._setup_tree_columns()

    def _setup_tree_columns(self):
        base_cols = ['Ping (ms)', 'Jitter', 'Anonymity', 'Country', 'Server', 'Port', 'URL']
        self.external_domains = [d.strip() for d in self.ping_to_var.get().split(',') if d.strip()]
        all_cols = base_cols + [f"Ping {d[:10]}" for d in self.external_domains]
        self.tree['columns'] = all_cols
        for col in all_cols:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_treeview(c, False))
            self.tree.column(col, width=110, anchor=tk.W)
        self.tree.column('Server', width=200)
        self.tree.column('URL', width=300)

    def _on_input_source_change(self):
        for widget in [self.url_entry, self.file_frame, self.text_frame]: widget.pack_forget()
        source = self.input_source_var.get()
        if source == "url": self.url_entry.pack(fill=tk.X, expand=True, pady=5)
        elif source == "file": self.file_frame.pack(fill=tk.X, expand=True, pady=5)
        elif source == "text": self.text_frame.pack(fill=tk.BOTH, expand=True, pady=5)

    def _browse_file(self):
        if filepath := filedialog.askopenfilename(title="Select Proxy File", filetypes=(("Text files", "*.txt"), ("All files", "*.*"))):
            self.file_path_var.set(filepath)

    def _thread_fetch_url(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            if not response.text.strip():
                self.result_queue.put(("URL_FETCH_ERROR", "The URL returned an empty file."))
                return
            self.result_queue.put(("URL_FETCH_SUCCESS", response.text))
        except requests.exceptions.HTTPError as e:
            self.result_queue.put(("URL_FETCH_ERROR", f"HTTP Error: {e.response.status_code} for URL: {url}"))
        except requests.exceptions.RequestException as e:
            self.result_queue.put(("URL_FETCH_ERROR", f"Failed to fetch URL. Check connection.\nError: {e}"))

    def _start_scan(self):
        if self.scan_running.is_set(): return
        self._clear_results(clear_inputs=False)
        self.scan_running.set()
        self._set_controls_state_on_scan_start()
        source = self.input_source_var.get()
        if source == "url":
            if not (url := self.url_entry.get()):
                messagebox.showerror("Input Error", "URL field cannot be empty.")
                self._scan_aborted()
                return
            self.status_var.set(f"Fetching proxies from URL...")
            threading.Thread(target=self._thread_fetch_url, args=(url,), daemon=True).start()
        else:
            self._get_proxies_from_source_and_proceed()

    def _get_proxies_from_source_and_proceed(self):
        source = self.input_source_var.get()
        urls = set()
        try:
            if source == "file":
                if not (filepath := self.file_path_var.get()): raise ValueError("No file selected.")
                with open(filepath, 'r', encoding='utf-8') as f: urls = {line.strip() for line in f if line.strip()}
            elif source == "text":
                if not (text_content := self.text_area.get("1.0", tk.END).strip()): raise ValueError("Text area is empty.")
                urls = {line.strip() for line in text_content.splitlines() if line.strip()}
            if not (parsed := [p for p in (parse_proxy_url(url) for url in urls) if p]):
                raise ValueError("Could not find any valid proxy URLs in the provided source.")
            self._proceed_with_scan(parsed)
        except (ValueError, ConnectionError) as e:
            messagebox.showerror("Input Error", str(e))
            self._scan_aborted()
        except Exception as e:
            messagebox.showerror("An Unexpected Error Occurred", f"An unexpected error occurred: {e}")
            self._scan_aborted()

    def _proceed_with_scan(self, proxies: List[Proxy]):
        self.proxies_to_check = proxies
        self.total_proxies = len(proxies)
        self.total_var.set(f"Total: {self.total_proxies}")
        self._setup_tree_columns()
        self.status_var.set(f"Found {self.total_proxies} proxies. Starting scan...")
        self.progress_bar['maximum'] = self.total_proxies
        threading.Thread(target=self._run_checker_logic, daemon=True).start()

    def _pause_scan(self):
        if self.scan_paused.is_set():
            self.scan_paused.clear()
            self.pause_button.config(text="Pause")
            self.status_var.set("Resuming scan...")
        else:
            self.scan_paused.set()
            self.pause_button.config(text="Resume")
            self.status_var.set("Scan paused.")

    def _stop_scan(self):
        if self.scan_running.is_set():
            self.scan_running.clear()
            self.scan_paused.clear()
            self.status_var.set("Stopping scan...")

    def _clear_all(self):
        if self.scan_running.is_set():
            messagebox.showwarning("Scan in Progress", "Cannot clear while a scan is running.")
            return
        if messagebox.askokcancel("Clear All", "This will clear all inputs and results. Are you sure?"):
            self._clear_results(clear_inputs=True)

    def _clear_results(self, clear_inputs: bool):
        self.tree.delete(*self.tree.get_children())
        self.results.clear()
        self.checked_proxies = 0
        self.healthy_proxies = 0
        self.progress_bar['value'] = 0
        self.progress_text_var.set("")
        self.status_var.set("Ready")
        self.total_var.set("Total: 0")
        self.healthy_var.set("Healthy: 0")
        self.failed_var.set("Failed: 0")
        self.file_menu.entryconfig("Save Results...", state="disabled")
        if clear_inputs:
            self.url_entry.delete(0, tk.END)
            self.file_path_var.set("")
            self.text_area.delete("1.0", tk.END)
            for var in [self.max_ping_var, self.min_ping_var, self.include_country_var, self.exclude_country_var, self.secret_var, self.top_n_var]:
                var.set("")

    def _set_controls_state_on_scan_start(self):
        self.start_button.config(state=tk.DISABLED, text="Scanning...")
        self.pause_button.config(state=tk.NORMAL, text="Pause")
        self.stop_button.config(state=tk.NORMAL)
        self.clear_button.config(state=tk.DISABLED)
        self.file_menu.entryconfig("Save Results...", state="disabled")
        for i in range(3): self.notebook.tab(i, state=tk.DISABLED)

    def _set_controls_state_on_scan_end(self):
        self.start_button.config(state=tk.NORMAL, text="Start Scan")
        self.pause_button.config(state=tk.DISABLED, text="Pause")
        self.stop_button.config(state=tk.DISABLED)
        self.clear_button.config(state=tk.NORMAL)
        for i in range(3): self.notebook.tab(i, state=tk.NORMAL)
    
    def _scan_aborted(self):
        self.scan_running.clear()
        self._set_controls_state_on_scan_end()
        self.status_var.set("Ready")

    def _scan_finished(self):
        self._apply_filters_and_sort()
        self._set_controls_state_on_scan_end()
        if self.results: self.file_menu.entryconfig("Save Results...", state="normal")
        final_status = "Scan stopped by user." if not self.scan_running.is_set() and self.checked_proxies < self.total_proxies else "Scan complete."
        self.status_var.set(f"{final_status} Found {len(self.results)} healthy proxies.")
        self.scan_running.clear()

    def _run_checker_logic(self):
        count, timeout, workers = self.count_var.get(), self.timeout_var.get(), self.workers_var.get()
        fetch_country = self.show_country_var.get() or self.include_country_var.get() or self.exclude_country_var.get()
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(check_proxy, p, count, timeout, fetch_country, self.external_domains) for p in self.proxies_to_check}
            for i, future in enumerate(as_completed(futures)):
                if not self.scan_running.is_set(): break
                while self.scan_paused.is_set():
                    self.after(100)
                if result := future.result(): self.result_queue.put(("RESULT", result))
                self.result_queue.put(("PROGRESS_UPDATE", i + 1))
        self.result_queue.put(("SCAN_COMPLETE", None))

    def _process_queue(self):
        try:
            while True:
                msg_type, data = self.result_queue.get_nowait()
                if msg_type == "URL_FETCH_SUCCESS":
                    urls = {line.strip() for line in data.splitlines() if line.strip()}
                    parsed = [p for p in (parse_proxy_url(url) for url in urls) if p]
                    if not parsed:
                        messagebox.showerror("Input Error", "Could not find any valid proxy URLs in the fetched file.")
                        self._scan_aborted()
                    else:
                        self._proceed_with_scan(parsed)
                elif msg_type == "URL_FETCH_ERROR":
                    messagebox.showerror("URL Fetch Error", data)
                    self._scan_aborted()
                elif msg_type == "PROGRESS_UPDATE":
                    self.checked_proxies = data
                    self.progress_bar.step(1)
                    self.progress_text_var.set(f"{self.checked_proxies}/{self.total_proxies}")
                    self.failed_var.set(f"Failed: {self.checked_proxies - self.healthy_proxies}")
                elif msg_type == "RESULT":
                    self.results.append(data)
                    self.healthy_proxies += 1
                    self.healthy_var.set(f"Healthy: {self.healthy_proxies}")
                    self._insert_result_into_tree(data)
                elif msg_type == "SCAN_COMPLETE": self._scan_finished()
        except queue.Empty:
            pass
        finally:
            self.after(100, self._process_queue)

    def _apply_filters_and_sort(self):
        try:
            criteria = FilterCriteria(
                max_ping=int(s) if (s := self.max_ping_var.get()) else None,
                min_ping=int(s) if (s := self.min_ping_var.get()) else None,
                include_countries=[c.strip().upper() for c in self.include_country_var.get().split(',')] if self.include_country_var.get() else None,
                exclude_countries=[c.strip().upper() for c in self.exclude_country_var.get().split(',')] if self.exclude_country_var.get() else None,
                require_secret=self.secret_var.get() or None,
                top_n=int(s) if (s := self.top_n_var.get()) else None,
            )
            self.results = filter_and_sort_proxies(self.results, criteria)
        except (ValueError, TypeError) as e:
            messagebox.showwarning("Filter Error", f"Invalid filter value: {e}")
        self._redraw_treeview()

    def _redraw_treeview(self):
        self.tree.delete(*self.tree.get_children())
        for proxy in self.results: self._insert_result_into_tree(proxy)

    def _insert_result_into_tree(self, proxy: Proxy):
        values = [proxy.ping, f"{proxy.jitter:.2f}", proxy.anonymity, proxy.country_code or "N/A", proxy.server, proxy.port, proxy.original_url]
        values.extend([str(proxy.ping_results.get(d)) if proxy.ping_results.get(d) is not None else 'N/A' for d in self.external_domains])
        self.tree.insert('', tk.END, values=tuple(values))
    
    def _show_context_menu(self, event):
        if selection := self.tree.identify_row(event.y):
            self.tree.selection_set(selection)
            self.context_menu.post(event.x_root, event.y_root)

    def _show_details_window(self, event):
        if not (selection := self.tree.selection()): return
        item_id = selection[0]
        selected_proxy = None
        for proxy in self.results:
            if proxy.original_url == self.tree.item(item_id, "values")[6]:
                selected_proxy = proxy
                break
        if not selected_proxy: return

        top = bst.Toplevel(self, title="Proxy Details")
        top.geometry("500x400")
        
        details_text = tk.Text(top, wrap="word", bg="#1c1c1c", fg="white", relief="flat")
        details_text.pack(expand=True, fill="both", padx=10, pady=10)
        
        details = asdict(selected_proxy)
        for key, value in details.items():
            details_text.insert(tk.END, f"{key.replace('_', ' ').title()}: ", "bold")
            details_text.insert(tk.END, f"{value}\n")
        details_text.tag_config("bold", font=("Helvetica", 10, "bold"))
        details_text.config(state="disabled")

    def _copy_url(self):
        if selection := self.tree.selection():
            url = self.tree.item(selection[0], "values")[6]
            self.clipboard_clear()
            self.clipboard_append(url)
            self.status_var.set("Copied URL to clipboard.")

    def _copy_row(self):
        if selection := self.tree.selection():
            row_values = self.tree.item(selection[0], "values")
            self.clipboard_clear()
            self.clipboard_append("\t".join(map(str, row_values)))
            self.status_var.set("Copied row to clipboard.")

    def _sort_treeview(self, col: str, reverse: bool):
        try:
            data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
            is_numeric = col in ['Ping (ms)', 'Jitter', 'Port'] or col.startswith('Ping ')
            def sort_key(item):
                val = item[0]
                if not is_numeric: return str(val).lower()
                try: return float(val)
                except (ValueError, TypeError): return float('inf')
            data.sort(key=sort_key, reverse=reverse)
            for index, (val, child) in enumerate(data): self.tree.move(child, '', index)
            for c in self.tree['columns']: self.tree.heading(c, text=c)
            arrow = ' ▼' if reverse else ' ▲'
            self.tree.heading(col, text=col + arrow, command=lambda: self._sort_treeview(col, not reverse))
        except (ValueError, tk.TclError):
            pass

    def _save_results(self):
        if not self.results:
            messagebox.showinfo("No Results", "There are no results to save.")
            return
        if not (filepath := filedialog.asksaveasfilename(title="Save Results", defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("JSON Files", "*.json")])):
            return
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if filepath.endswith('.json'):
                    json.dump([asdict(p) for p in self.results], f, indent=2)
                elif filepath.endswith('.csv'):
                    headers = ['ping', 'jitter', 'anonymity', 'country_code', 'server', 'port', 'url'] + [f'ping_{d}' for d in self.external_domains]
                    writer = csv.writer(f)
                    writer.writerow(headers)
                    for p in self.results:
                        row = [p.ping, p.jitter, p.anonymity, p.country_code, p.server, p.port, p.original_url]
                        row.extend([p.ping_results.get(d) for d in self.external_domains])
                        writer.writerow(row)
                else:
                    for p in self.results: f.write(f"{p.original_url}\n")
            messagebox.showinfo("Success", f"Results successfully saved to {filepath}")
        except IOError as e:
            messagebox.showerror("Save Error", f"Failed to save file: {e}")
    
    def _show_about_dialog(self):
        about_text = (
            f"Advanced Proxy Latency Checker v{__version__}\n\n"
            f"Copyright 2025, {__author__}\n"
            "Licensed under the MIT License.\n\n"
            "A high-performance utility for testing and evaluating proxy servers.\n"
            "For more information, visit the GitHub repository."
        )
        messagebox.showinfo("About", about_text)

if __name__ == "__main__":
    app = ProxyCheckerGUI()
    app.mainloop()
