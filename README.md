# Advanced Proxy Latency Checker

## Project Overview

The Advanced Proxy Latency Checker is a robust, high-performance software utility designed for network administrators, developers, and security professionals. It provides a comprehensive solution for testing and evaluating proxy servers. The tool is engineered to handle large lists of proxies efficiently, leveraging concurrent processing to deliver rapid results.

This project offers two distinct interfaces: a full-featured Graphical User Interface (GUI) for interactive use and a powerful Command-Line Interface (CLI) optimized for scripting, automation, and integration into larger workflows. The primary function is to measure critical performance metrics, including latency (ping) and jitter, and to enrich this data with geolocation information.

## Core Features

This utility is built with a focus on performance, accuracy, and usability.

* **High-Concurrency Engine**: The application utilizes a multi-threaded architecture to check hundreds or even thousands of proxies simultaneously, significantly reducing the time required to process large lists.

* **Dual-Interface Design**:
    * **Graphical User Interface (GUI)**: An intuitive and responsive interface built with Tkinter, providing real-time feedback, interactive controls for filtering and sorting, and straightforward options for loading and saving proxy lists.
    * **Command-Line Interface (CLI)**: A comprehensive CLI with full parity, designed for power users and automation. It supports a wide range of arguments for fine-grained control over the checking process and output formats.

* **Multiple Input Sources**:
    * **URL**: Fetch proxy lists directly from a remote URL. The GUI is pre-configured with a default URL for immediate use.
    * **Local File**: Load proxies from a local text file, with one proxy URL per line. The CLI will automatically use `update_proxies.txt` if it exists in the project root and no other input is specified.
    * **Text Input / Stdin**: Paste proxies directly into the GUI's text area or pipe them into the CLI via standard input.

* **Comprehensive Performance Metrics**:
    * **Latency (Ping)**: Calculates the average round-trip time in milliseconds for multiple connection attempts to each proxy server.
    * **Jitter**: Measures the standard deviation of the latency measurements, providing a key indicator of connection stability.

* **Geolocation Identification**:
    * Optionally fetches the geographical location (Country Code and Country Name) for each proxy by resolving its IP address through the ip-api.com service.

* **Advanced Filtering and Sorting**:
    * Filter results based on a maximum ping threshold to exclude slow proxies.
    * Filter results by specific ISO 3166-1 alpha-2 country codes.
    * Limit the output to the top 'N' best-performing proxies based on the selected sorting criteria.
    * Sort results by either latency or jitter to prioritize speed or stability.

* **Flexible Output Formats**:
    * Save filtered and sorted lists of healthy proxies in multiple formats:
        * **Plain Text (.txt)**: A simple list of proxy URLs.
        * **CSV (.csv)**: A comma-separated values file with detailed metrics in columns.
        * **JSON (.json)**: A structured JSON array of objects, ideal for programmatic use.

## Project Architecture

The codebase is organized into a clean, modular structure to promote maintainability and separation of concerns.

* `src/core/checker.py`: This module contains the backend logic. All core functionalities, including the `Proxy` data class, latency measurement, geolocation fetching, and URL parsing, are centralized here. This ensures that both the GUI and CLI operate on the same reliable foundation.
* `src/gui.py`: The implementation of the Tkinter-based Graphical User Interface. It handles user interaction, manages the application state, and invokes the core checker functions in a separate thread to maintain a responsive UI. It imports icon data from `icon.py`.
* `src/cli.py`: The implementation of the Command-Line Interface. It uses Python's `argparse` module to provide a rich set of commands and options for users who prefer or require a terminal-based workflow.
* `src/icon.py`: A dedicated module to store the base64-encoded application icon, keeping the main GUI script clean.

## Installation and Setup

The following steps are required to set up the project locally. A Python version of 3.7 or higher is required. The use of a virtual environment is strongly recommended to isolate dependencies and avoid conflicts.

1.  **Clone the Repository**:
    ```bash
    git clone [https://github.com/vafaeim/advanced-proxy-checker.git](https://github.com/vafaeim/advanced-proxy-checker.git)
    cd advanced-proxy-checker
    ```

2.  **Create and Activate a Virtual Environment**:
    * On macOS and Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    * On Windows:
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```

3.  **Install Required Dependencies**:
    The project relies on a small number of external libraries, which are listed in `requirements.txt`. Install them using pip.
    ```bash
    pip install -r requirements.txt
    ```

## Usage Instructions

The application can be executed via its graphical or command-line interface.

### Graphical User Interface (GUI)

The GUI is designed for ease of use and provides a complete visual toolset for managing the proxy checking process.

* **To Launch the GUI**:
    ```bash
    python src/gui.py
    ```

* **Operating the GUI**:
    1.  **Select Input Source**: Choose between "URL", "File", or "Text" radio buttons.
        * **URL**: The application defaults to a pre-filled URL containing an updated list of proxies. You may change this to any valid URL.
        * **File**: Click "Browse..." to select a local `.txt` file containing your proxies.
        * **Text**: Paste a list of proxy URLs directly into the text field.
    2.  **Configure Settings**: Adjust the "Ping Count", "Timeout", and "Workers" (concurrent threads) as needed.
    3.  **Set Filters**: Optionally, enter a "Max Ping" value or a "Top N Results" limit. Check "Fetch & Show Country" to enable geolocation.
    4.  **Start Scan**: Click the "Start Scan" button to begin the process. The progress bar will indicate the status, and results will populate in the table in real-time.
    5.  **View and Sort Results**: Click on any column header in the results table to sort the data.
    6.  **Save Results**: Once the scan is complete, click "Save Results..." to save the filtered list to a `.txt`, `.csv`, or `.json` file.

### Command-Line Interface (CLI)

The CLI is the preferred method for automation, scripting, and headless environments. If no input source is provided, the CLI will automatically look for and use `update_proxies.txt` in the current directory.

* **General Syntax**:
    ```bash
    python src/cli.py [input_source] [options]
    ```

* **CLI Arguments**:
    * `file_path`: (Positional) Path to a file with proxy URLs. Defaults to `update_proxies.txt` if present.
    * `--url URL`: Fetch proxies from a remote URL.
    * `--stdin`: Read proxies from standard input.
    * `--top N`: Limit the output to the top N results.
    * `--max-ping MS`: Exclude proxies with a ping higher than MS milliseconds.
    * `--country CC [CC ...]`: Include only proxies from the specified country codes.
    * `--sort-by {ping,jitter}`: Sort results by the specified metric.
    * `-o, --output FILE`: Path to save the output file.
    * `--csv, --json`: Set the output format. Defaults to plain text if not specified.
    * `--silent`: Suppress all non-error console output.
    * `-c, --count N`: Number of pings per proxy.
    * `-t, --timeout S`: Connection timeout in seconds.
    * `-w, --workers N`: Number of concurrent worker threads.
    * `--version`: Display the application version.
    * `--help`: Display the help message with all available commands.

* **CLI Examples**:

    1.  **Check proxies using the default `update_proxies.txt` and display the top 10 fastest results**:
        ```bash
        python src/cli.py --top 10
        ```

    2.  **Check proxies from the repository's default URL, filter for those in Germany (DE) with a ping under 400ms, and show country info**:
        ```bash
        python src/cli.py --url [https://raw.githubusercontent.com/vafaeim/advanced-proxy-checker/main/update_proxies.txt](https://raw.githubusercontent.com/vafaeim/advanced-proxy-checker/main/update_proxies.txt) --max-ping 400 --country DE
        ```

    3.  **Read proxies from standard input, check them, and save the results as a JSON file**:
        ```bash
        cat my_proxies.txt | python src/cli.py --stdin --json -o results.json
        ```

## Default Proxy List

This repository includes `update_proxies.txt`, a file containing a list of publicly available proxies for demonstration and immediate use. This file is maintained and updated periodically.

* **GUI**: The GUI is pre-configured to use the raw version of this file directly from the GitHub repository, ensuring that users always have a fresh list to start with.
* **CLI**: The CLI will automatically use the local `update_proxies.txt` file as its default input source if it exists in the project's root directory and no other source is specified.

The direct raw link to the file is:
`https://raw.githubusercontent.com/vafaeim/advanced-proxy-checker/main/update_proxies.txt`

## Author

This project was created and is maintained by Amirreza Vafaei Moghadam.

* **GitHub Profile**: https://github.com/vafaeim

## Contribution Guidelines

Contributions to this project are welcome. If you wish to contribute, please follow these standard guidelines:

1.  **Fork the Repository**: Create a personal fork of the project on GitHub.
2.  **Create a Feature Branch**: Make a new branch for your changes (`git checkout -b feature/MyNewFeature`).
3.  **Commit Changes**: Commit your changes with a clear and descriptive message that explains the purpose of your contribution.
4.  **Push to Your Branch**: Push your feature branch to your forked repository (`git push origin feature/MyNewFeature`).
5.  **Open a Pull Request**: Submit a pull request from your feature branch to the main branch of the original repository. Please provide a detailed description of your changes and reference any relevant issues.

## License

This project is licensed under the MIT License. Please see the `LICENSE` file in the repository for full details. The MIT License is a permissive free software license originating at the Massachusetts Institute of Technology (MIT) in the late 1980s. As a permissive license, it puts only very limited restriction on reuse and has, therefore, high license compatibility.