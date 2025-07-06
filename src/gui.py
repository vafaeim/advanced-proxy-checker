#!/usr/bin/env python3
# src/gui.py
"""
Graphical User Interface for the Advanced Proxy Latency Checker.

This application provides a user-friendly interface to check proxies,
view results in real-time, and save them to a file.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import requests
import threading
import queue
import csv
import json
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

# --- Local Imports ---
from core.checker import Proxy, check_proxy, parse_proxy_url
from icon import ICON_DATA  # Import the icon data

# --- Metadata ---
__author__ = "Amirreza Vafaei Moghadam"
__version__ = "3.2.0"
__license__ = "MIT"
__copyright__ = f"Copyright 2025, {__author__}"

# --- Constants ---
DEFAULT_TIMEOUT = 2
DEFAULT_WORKERS = 20
DEFAULT_PING_COUNT = 3
URL_PLACEHOLDER = "https://raw.githubusercontent.com/vafaeim/advanced-proxy-checker/main/update_proxies.txt"


class ProxyCheckerGUI(tk.Tk):
    """The main application window for the proxy checker GUI."""

    def __init__(self):
        super().__init__()
        self.title(f"Advanced Proxy Latency Checker v{__version__}")
        self.geometry("1100x750")
        self.minsize(800, 600)

        # --- Set Application Icon ---
        try:
            icon_bytes = base64.b64decode(ICON_DATA)
            icon_image = tk.PhotoImage(data=icon_bytes)
            self.iconphoto(True, icon_image)
        except tk.TclError:
            print("Warning: Could not set application icon. Your environment might not support it.")

        # --- Member State ---
        self.proxies_to_check: List[Proxy] = []
        self.results: List[Proxy] = []
        self.result_queue = queue.Queue()
        self.is_running = threading.Event()

        self._configure_styles()
        self._create_widgets()
        self.after(100, self._process_queue)

    def _configure_styles(self):
        """Configures ttk styles for the application."""
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TLabel", padding=5)
        style.configure("TButton", padding=5)
        style.configure("TFrame", padding=10)
        style.configure("TLabelframe.Label", font=("Helvetica", 10, "bold"))
        style.configure("Header.TLabel", font=("Helvetica", 10, "bold"))

    def _create_widgets(self):
        """Creates and lays out all widgets in the main window."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # --- Left Pane: Controls ---
        controls_frame = ttk.Frame(paned_window, width=380)
        self._create_controls_pane(controls_frame)
        paned_window.add(controls_frame, weight=1)

        # --- Right Pane: Results ---
        results_frame = ttk.Frame(paned_window)
        self._create_results_pane(results_frame)
        paned_window.add(results_frame, weight=3)

        # --- Bottom: Status Bar ---
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _create_controls_pane(self, parent: ttk.Frame):
        """Creates all widgets for the left-side controls pane."""
        # Input Source
        self._create_input_source_widgets(parent)
        # Connection Settings
        self._create_connection_widgets(parent)
        # Filtering
        self._create_filtering_widgets(parent)
        # Action Buttons
        self._create_action_buttons(parent)

    def _create_input_source_widgets(self, parent: ttk.Frame):
        """Widgets for selecting and providing proxy sources."""
        frame = ttk.LabelFrame(parent, text="Input Source", padding=10)
        frame.pack(fill=tk.X, pady=5)
        
        self.input_source_var = tk.StringVar(value="url")
        
        # Radio buttons
        radio_frame = ttk.Frame(frame)
        radio_frame.pack(fill=tk.X)
        ttk.Radiobutton(radio_frame, text="URL", variable=self.input_source_var, value="url", command=self._on_input_source_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(radio_frame, text="File", variable=self.input_source_var, value="file", command=self._on_input_source_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(radio_frame, text="Text", variable=self.input_source_var, value="text", command=self._on_input_source_change).pack(side=tk.LEFT, padx=5)

        # Dynamic input area
        self.input_area = ttk.Frame(frame, height=150)
        self.input_area.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.url_entry = ttk.Entry(self.input_area)
        self.url_entry.insert(0, URL_PLACEHOLDER)
        
        self.file_frame = ttk.Frame(self.input_area)
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path_var, state='readonly')
        self.file_button = ttk.Button(self.file_frame, text="Browse...", command=self._browse_file)
        self.file_entry.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=(0, 5))
        self.file_button.pack(side=tk.RIGHT)

        self.text_area = tk.Text(self.input_area, height=8, undo=True)
        self.text_scroll = ttk.Scrollbar(self.input_area, orient="vertical", command=self.text_area.yview)
        self.text_area['yscrollcommand'] = self.text_scroll.set
        
        self._on_input_source_change()

    def _create_connection_widgets(self, parent: ttk.Frame):
        """Widgets for configuring connection parameters."""
        frame = ttk.LabelFrame(parent, text="Connection Settings", padding=10)
        frame.pack(fill=tk.X, pady=5)
        frame.grid_columnconfigure(1, weight=1)

        ttk.Label(frame, text="Ping Count:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.count_var = tk.IntVar(value=DEFAULT_PING_COUNT)
        ttk.Spinbox(frame, from_=1, to=20, width=5, textvariable=self.count_var).grid(row=0, column=1, sticky=tk.W, pady=2)

        ttk.Label(frame, text="Timeout (s):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.timeout_var = tk.IntVar(value=DEFAULT_TIMEOUT)
        ttk.Spinbox(frame, from_=1, to=60, width=5, textvariable=self.timeout_var).grid(row=1, column=1, sticky=tk.W, pady=2)

        ttk.Label(frame, text="Workers:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.workers_var = tk.IntVar(value=DEFAULT_WORKERS)
        ttk.Spinbox(frame, from_=1, to=100, width=5, textvariable=self.workers_var).grid(row=2, column=1, sticky=tk.W, pady=2)

    def _create_filtering_widgets(self, parent: ttk.Frame):
        """Widgets for filtering the final results."""
        frame = ttk.LabelFrame(parent, text="Filtering", padding=10)
        frame.pack(fill=tk.X, pady=5)
        frame.grid_columnconfigure(1, weight=1)
        
        ttk.Label(frame, text="Max Ping (ms):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.max_ping_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.max_ping_var).grid(row=0, column=1, sticky=tk.EW, pady=2)

        ttk.Label(frame, text="Top N Results:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.top_n_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.top_n_var).grid(row=1, column=1, sticky=tk.EW, pady=2)
        
        self.show_country_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Fetch & Show Country", variable=self.show_country_var).grid(row=2, columnspan=2, sticky=tk.W, pady=5)

    def _create_action_buttons(self, parent: ttk.Frame):
        """Widgets for starting/stopping the scan and saving results."""
        frame = ttk.Frame(parent, padding=(0, 10))
        frame.pack(fill=tk.X)
        frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.start_button = ttk.Button(frame, text="Start Scan", command=self._start_scan)
        self.start_button.grid(row=0, column=0, sticky=tk.EW, padx=(0, 5))
        
        self.stop_button = ttk.Button(frame, text="Stop", command=self._stop_scan, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, sticky=tk.EW, padx=5)

        self.save_button = ttk.Button(frame, text="Save Results...", command=self._save_results, state=tk.DISABLED)
        self.save_button.grid(row=0, column=2, sticky=tk.EW, padx=(5, 0))

    def _create_results_pane(self, parent: ttk.Frame):
        """Creates all widgets for the right-side results pane."""
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(parent, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2)

        cols = ('Ping (ms)', 'Jitter', 'Server', 'Port', 'Country', 'URL')
        self.tree = ttk.Treeview(parent, columns=cols, show='headings')
        self.tree_cols = cols
        for col in cols:
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_treeview(c, False))
            self.tree.column(col, width=100, anchor=tk.W)
        
        self.tree.column('Server', width=200)
        self.tree.column('URL', width=300)

        tree_scroll = ttk.Scrollbar(parent, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        self.tree.grid(row=1, column=0, sticky="nsew")
        tree_scroll.grid(row=1, column=1, sticky="ns")

    # --- Widget Logic and Callbacks ---

    def _on_input_source_change(self):
        """Hides and shows the relevant input widget based on radio selection."""
        source = self.input_source_var.get()
        # Forget all widgets first
        self.url_entry.pack_forget()
        self.file_frame.pack_forget()
        self.text_area.pack_forget()
        self.text_scroll.pack_forget()

        if source == "url":
            self.url_entry.pack(fill=tk.X, expand=True, in_=self.input_area)
        elif source == "file":
            self.file_frame.pack(fill=tk.X, expand=True, in_=self.input_area)
        elif source == "text":
            self.text_scroll.pack(side=tk.RIGHT, fill=tk.Y, in_=self.input_area)
            self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, in_=self.input_area)

    def _browse_file(self):
        """Opens a file dialog to select a proxy list file."""
        filepath = filedialog.askopenfilename(
            title="Select Proxy File",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*"))
        )
        if filepath:
            self.file_path_var.set(filepath)

    def _get_proxies_from_source(self) -> Optional[List[Proxy]]:
        """Fetches proxy URLs from the selected source and parses them."""
        source = self.input_source_var.get()
        urls = set()
        try:
            if source == "file":
                if not (filepath := self.file_path_var.get()): raise ValueError("No file selected.")
                with open(filepath, 'r', encoding='utf-8') as f: urls = {line.strip() for line in f if line.strip()}
            elif source == "url":
                if not (url := self.url_entry.get()): raise ValueError("No URL provided.")
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                urls = {line.strip() for line in response.text.splitlines() if line.strip()}
            elif source == "text":
                if not (text_content := self.text_area.get("1.0", tk.END).strip()): raise ValueError("Text area is empty.")
                urls = {line.strip() for line in text_content.splitlines() if line.strip()}
            
            parsed = [p for p in (parse_proxy_url(url) for url in urls) if p]
            if not parsed:
                raise ValueError("No valid proxy URLs found in the provided source.")
            return parsed

        except Exception as e:
            messagebox.showerror("Input Error", f"Failed to get proxies: {e}")
            return None

    # --- Core Application Logic ---

    def _start_scan(self):
        """Initiates the proxy scanning process."""
        if self.is_running.is_set():
            return

        self._clear_results()
        self.proxies_to_check = self._get_proxies_from_source()
        if not self.proxies_to_check:
            self.status_var.set("Ready")
            return
        
        self.is_running.set()
        self._set_controls_state(tk.DISABLED)
        self.status_var.set(f"Found {len(self.proxies_to_check)} proxies. Starting scan...")
        self.progress_bar['maximum'] = len(self.proxies_to_check)
        
        threading.Thread(target=self._run_checker_logic, daemon=True).start()

    def _stop_scan(self):
        """Stops the currently running scan."""
        if self.is_running.is_set():
            self.is_running.clear()
            self.status_var.set("Stopping scan...")

    def _clear_results(self):
        """Clears the results tree and resets state."""
        self.tree.delete(*self.tree.get_children())
        self.results.clear()
        self.progress_bar['value'] = 0
        self.save_button['state'] = tk.DISABLED

    def _set_controls_state(self, state: str):
        """Enables or disables UI controls during scanning."""
        self.start_button['state'] = state
        self.save_button['state'] = tk.DISABLED # Always disable save during scan
        self.stop_button['state'] = tk.NORMAL if state == tk.DISABLED else tk.DISABLED
        # You could expand this to disable all input widgets as well
    
    def _scan_finished(self):
        """Called when the scan is complete or stopped."""
        self._apply_filters_and_sort()
        self._set_controls_state(tk.NORMAL)
        if self.results:
            self.save_button['state'] = tk.NORMAL
        
        final_status = "Scan stopped." if not self.is_running.is_set() else "Scan complete."
        self.status_var.set(f"{final_status} Found {len(self.results)} healthy proxies.")
        self.is_running.clear()

    def _run_checker_logic(self):
        """The core worker thread logic for checking proxies."""
        count = self.count_var.get()
        timeout = self.timeout_var.get()
        workers = self.workers_var.get()
        fetch_country = self.show_country_var.get()
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(check_proxy, p, count, timeout, fetch_country) for p in self.proxies_to_check}
            for future in as_completed(futures):
                if not self.is_running.is_set():
                    break # Exit loop if stop was requested
                if result := future.result():
                    self.result_queue.put(result)
                self.result_queue.put("PROGRESS_UPDATE")
        
        self.result_queue.put("SCAN_COMPLETE")

    def _process_queue(self):
        """Processes messages from the worker thread queue in the main thread."""
        try:
            while True: # Process all available messages
                msg = self.result_queue.get_nowait()
                if isinstance(msg, Proxy):
                    self.results.append(msg)
                    self._insert_result_into_tree(msg)
                elif msg == "PROGRESS_UPDATE":
                    self.progress_bar.step(1)
                elif msg == "SCAN_COMPLETE":
                    self._scan_finished()
        except queue.Empty:
            pass # No more messages
        finally:
            # Reschedule after 100ms
            self.after(100, self._process_queue)

    def _insert_result_into_tree(self, proxy: Proxy):
        """Inserts a single proxy result into the results treeview."""
        values = (
            proxy.ping,
            f"{proxy.jitter:.2f}",
            proxy.server,
            proxy.port,
            proxy.country_code or "N/A",
            proxy.original_url
        )
        self.tree.insert('', tk.END, values=values)

    def _apply_filters_and_sort(self):
        """Applies final filters and sorting to the results."""
        filtered = self.results.copy()
        try:
            if max_ping_str := self.max_ping_var.get():
                filtered = [p for p in filtered if p.ping <= int(max_ping_str)]
        except (ValueError, TypeError): pass
        
        filtered.sort(key=lambda p: p.ping)

        try:
            if top_n_str := self.top_n_var.get():
                filtered = filtered[:int(top_n_str)]
        except (ValueError, TypeError): pass

        self.results = filtered
        self._redraw_treeview()

    def _redraw_treeview(self):
        """Clears and redraws the treeview with current results."""
        self.tree.delete(*self.tree.get_children())
        for proxy in self.results:
            self._insert_result_into_tree(proxy)

    def _sort_treeview(self, col: str, reverse: bool):
        """Sorts the treeview by a specific column."""
        try:
            data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
            
            # Determine sort type (numeric or string)
            is_numeric = col in ['Ping (ms)', 'Jitter', 'Port']
            key_func = (lambda item: float(item[0])) if is_numeric else (lambda item: str(item[0]).lower())
            
            data.sort(key=key_func, reverse=reverse)

            for index, (val, child) in enumerate(data):
                self.tree.move(child, '', index)

            # Update heading to show sort direction
            for c in self.tree_cols:
                self.tree.heading(c, text=c) # Reset others
            arrow = ' ▼' if reverse else ' ▲'
            self.tree.heading(col, text=col + arrow, command=lambda: self._sort_treeview(col, not reverse))
        except (ValueError, tk.TclError):
            # Handle cases where conversion fails (e.g., sorting 'N/A')
            pass

    def _save_results(self):
        """Saves the current list of results to a file."""
        if not self.results:
            messagebox.showinfo("No Results", "There are no results to save.")
            return
        
        filepath = filedialog.asksaveasfilename(
            title="Save Results",
            defaultextension=".txt", 
            filetypes=[("Text Files", "*.txt"), ("CSV Files", "*.csv"), ("JSON Files", "*.json")]
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                if filepath.endswith('.json'):
                    json.dump([asdict(p) for p in self.results], f, indent=2)
                elif filepath.endswith('.csv'):
                    writer = csv.writer(f)
                    writer.writerow(['ping', 'jitter', 'server', 'port', 'country_code', 'url'])
                    for p in self.results:
                        writer.writerow([p.ping, p.jitter, p.server, p.port, p.country_code, p.original_url])
                else:
                    for p in self.results:
                        f.write(f"{p.original_url}\n")
            messagebox.showinfo("Success", f"Results successfully saved to {filepath}")
        except IOError as e:
            messagebox.showerror("Save Error", f"Failed to save file: {e}")


if __name__ == "__main__":
    app = ProxyCheckerGUI()
    app.mainloop()
