# Concurrent File Downloader

A multi-threaded file downloader application built with Python and PyQt5, featuring a graphical user interface that allows users to download multiple files simultaneously with progress tracking and interrupt functionality.

![thumbnail_1](https://github.com/user-attachments/assets/8108fd9f-d58f-4b33-a924-47b0a2f64ef5)

## Features

- Concurrent downloads using Python threading
- Real-time progress tracking for each download
- Ability to interrupt individual or all downloads
- Clean and intuitive graphical interface
- Download queue management
- Automatic filename detection from URLs
- Error handling and status reporting

## Requirements

- Python 3.6+
- PyQt5
- requests

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/concurrent-file-downloader.git

# Navigate to the project directory
cd concurrent-file-downloader

# Install required packages
pip install PyQt5 requests
```

## Usage

Run the application using Python:

```bash
python concurrent_file_downloader.py
```

### Basic Operations

1. **Adding Downloads**
   - Enter a URL in the input field
   - Click "Add Download" or press Enter
   - The download will appear in the queue

2. **Starting Downloads**
   - Click "Start All Downloads" to begin downloading all queued files
   - Downloads will begin automatically and show progress in real-time

3. **Managing Downloads**
   - Use the "Interrupt" button on individual downloads to stop them
   - Click "Interrupt All" to stop all active downloads
   - Use "Clear List" to remove all downloads from the queue

## Technical Details

### Architecture

The application is built using three main classes:

#### 1. DownloadThread
- Inherits from `QThread`
- Handles the actual file-downloading process
- Implements interruption mechanism
- Emits signals for progress updates and completion status

```python
Signals:
- progress_signal(str, int): Emits download progress (thread_id, percentage)
- finished_signal(str): Emits when download completes (thread_id)
- error_signal(str, str): Emits when an error occurs (thread_id, error_message)
```

#### 2. DownloadWidget
- Inherits from `QFrame`
- Represents a single download item in the UI
- Contains progress bar, status label, and interrupt button
- Manages its own download thread

#### 3. DownloaderApp
- Inherits from `QMainWindow`
- Main application window
- Manages multiple download widgets
- Provides global controls for all downloads

### Key Features Implementation

#### Concurrent Downloads
The application achieves concurrent downloads by creating a separate `DownloadThread` for each download. Each thread:
- Runs independently of other downloads
- Uses the `requests` library with streaming enabled
- Processes data in chunks to provide progress updates
- Can be interrupted at any time

```python
def run(self):
    try:
        response = requests.get(self.url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        
        with open(self.save_path, 'wb') as f:
            downloaded = 0
            for data in response.iter_content(chunk_size=4096):
                if self._is_interrupted:
                    raise InterruptedError("Download interrupted by user")
                downloaded += len(data)
                f.write(data)
                progress = int((downloaded / total_size) * 100)
                self.progress_signal.emit(self.download_id, progress)
```

#### Interrupt Mechanism
Downloads can be interrupted at any time using a flag-based approach:
- Each download thread maintains an `_is_interrupted` flag
- The flag is checked during download chunks processing
- When interrupted, the partial download is cleaned up

#### Progress Tracking
Progress tracking is implemented using PyQt's signal-slot mechanism:
- Download progress is calculated based on downloaded bytes vs total size
- Progress updates are emitted via signals
- The UI updates in real time without blocking the main thread

## Error Handling

The application implements comprehensive error handling:

1. **Network Errors**
   - Connection failures
   - Invalid URLs
   - Server errors

2. **File System Errors**
   - Permission issues
   - Disk space problems
   - File access errors

3. **Interrupt Handling**
   - Clean cancellation of downloads
   - Removal of partial downloads
   - UI state management

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- PyQt5 for the GUI framework
- Requests library for HTTP functionality
- Python threading for concurrent operations
