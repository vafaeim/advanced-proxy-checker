# Advanced Proxy Latency Checker

## Project Overview

The Advanced Proxy Latency Checker is a robust, high-performance software utility designed for network administrators, developers, and security professionals. It provides a comprehensive solution for testing and evaluating proxy servers. The tool is engineered to handle large lists of proxies efficiently, leveraging concurrent processing to deliver rapid results.

This project offers two distinct interfaces: a full-featured Graphical User Interface (GUI) for interactive use and a powerful Command-Line Interface (CLI) optimized for scripting, automation, and integration into larger workflows. The primary function is to measure critical performance metrics, including latency (ping) and jitter, and to enrich this data with geolocation information, anonymity level, and the performance of proxies when connecting to external domains.

## Core Features

This utility is built with a focus on performance, accuracy, and a professional user experience.

* **Modern Graphical User Interface**:
    * Built with the `ttkbootstrap` library using the "darkly" theme for a sleek, modern, and professional appearance.
    * **Tabbed Interface**: Settings are neatly organized into "Source," "Connection," and "Filtering & Sorting" tabs, providing an uncluttered and intuitive workflow.
    * **Live Dashboard**: A real-time dashboard displays key statistics as the scan progresses, including Total, Healthy, and Failed proxy counts.
    * **Graphical Analysis Dashboard**: A dedicated "Analysis" tab automatically generates multiple charts after a scan, offering instant visual insights into your results, including:
        * Top 10 Countries by Proxy Count (Bar Chart).
        * Top 10 Most Used Proxy Ports (Bar Chart).
        * Anonymity Level Distribution (Pie Chart).
    * **Configuration Persistence**: The application saves all your settings—including window size, last-used inputs, and filter configurations—to a `config.json` file, restoring your workflow seamlessly on the next launch.

* **Advanced Proxy Testing**:
    * **High-Concurrency Engine**: Utilizes a multi-threaded architecture to check hundreds or even thousands of proxies simultaneously.
    * **Pause & Resume Functionality**: Gives you full control to pause long scans and resume them later.
    * **Anonymity Level Check**: Determines if a proxy is "Elite," "Anonymous," or "Transparent," providing crucial privacy information.
    * **Ping-Through-Proxy**: Measures the latency not just to the proxy server itself, but also *through* the proxy to specified external domains (e.g., `google.com`), giving a more accurate picture of real-world performance.
    * **Detailed Information Window**: Double-click any result to open a new window with a detailed breakdown of all its metrics.

* **Comprehensive Functionality**:
    * **Multiple Input Sources**: Load proxies from a remote URL, a local file, or by pasting them directly into the text area. The CLI also supports standard input.
    * **Advanced Filtering**: Filter results by a range of criteria, including max/min ping, included/excluded country codes, and required text in the proxy's secret.
    * **Flexible Output Formats**: Save filtered and sorted lists of healthy proxies as `.txt`, `.csv`, or `.json`.
    * **Robust Error Handling**: The GUI and CLI provide specific, user-friendly error messages to help diagnose issues with network connections, URLs, or input files.

## Project Architecture

The codebase is organized into a clean, modular structure to promote maintainability and separation of concerns.

* `src/core/checker.py`: This module contains the backend logic. All core functionalities, including the `Proxy` data class, latency measurement, anonymity checking, geolocation fetching, and result filtering, are centralized here.
* `src/gui.py`: The implementation of the Tkinter-based Graphical User Interface, enhanced with the `ttkbootstrap` library.
* `src/cli.py`: The implementation of the Command-Line Interface, providing full feature parity for scripting and automation.
* `src/assets.py`: A dedicated module to store base64-encoded application assets, such as icons.
* `config.json`: A file created automatically to store user preferences and application state between sessions.

## Installation and Setup

The following steps are required to set up the project locally. A Python version of 3.7 or higher is required. The use of a virtual environment is strongly recommended to isolate dependencies.

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
    This version requires `ttkbootstrap` for the GUI and `matplotlib` for the analysis charts.
    ```bash
    pip install -r requirements.txt
    ```

## Usage Instructions

The application can be executed via its graphical or command-line interface.

### Graphical User Interface (GUI)

The GUI is designed for a rich, interactive experience and provides a complete visual toolset for managing the proxy checking process.

* **To Launch the GUI**:
    ```bash
    python src/gui.py
    ```

* **Operating the GUI**:
    1.  **Configure Settings**: Navigate through the "Source," "Connection," and "Filtering & Sorting" tabs to set up your scan parameters.
    2.  **Start Scan**: Click the "Start Scan" button. The button will update to "Scanning..." and the dashboard and progress bar will provide live feedback.
    3.  **Control the Scan**: Use the "Pause"/"Resume" and "Stop" buttons to manage the scanning process.
    4.  **Analyze Results**: View results in the "Results Table" tab. Double-click any row for details, or switch to the "Analysis" tab to see graphical summaries of the data.
    5.  **Save Results**: Once the scan is complete, use the `File > Save Results...` menu item or the `Ctrl+S` shortcut to save the data.

### Command-Line Interface (CLI)

The CLI is the preferred method for automation, scripting, and headless environments. If no input source is provided, the CLI will automatically look for and use `update_proxies.txt` in the current directory.

* **General Syntax**:
    ```bash
    python src/cli.py [input_source] [options]
    ```

* **CLI Examples**:

    1.  **Check proxies using the default `update_proxies.txt`, ping Google through them, and show the top 10 results**:
        ```bash
        python src/cli.py --top 10 --ping-to google.com
        ```

    2.  **Check proxies from a URL, filtering for elite proxies in Germany (DE) with a ping under 400ms**:
        ```bash
        python src/cli.py --url [https://raw.githubusercontent.com/vafaeim/advanced-proxy-checker/main/update_proxies.txt](https://raw.githubusercontent.com/vafaeim/advanced-proxy-checker/main/update_proxies.txt) --max-ping 400 --country DE
        ```

    3.  **Read proxies from standard input and save the results as a JSON file**:
        ```bash
        cat my_proxies.txt | python src/cli.py --stdin --json -o results.json
        ```

    4.  **View all available commands and options**:
        ```bash
        python src/cli.py --help
        ```

## Default Proxy List

This repository includes `update_proxies.txt`, a file containing a list of publicly available proxies for demonstration and immediate use. This file is maintained and updated periodically. The GUI is pre-configured to use the raw version of this file from the GitHub repository, and the CLI will use the local version as its default input source if no other source is specified.

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

This project is licensed under the MIT License. Please see the `LICENSE` file in the repository for full details. The MIT License is a permissive free software license that puts very limited restriction on reuse and has high license compatibility.