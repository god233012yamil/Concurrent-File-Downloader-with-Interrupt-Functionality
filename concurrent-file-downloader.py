from typing import List, Optional
import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QPushButton, QLineEdit, QProgressBar, QLabel, 
                           QScrollArea, QFrame, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import QThread, pyqtSignal
import requests
import uuid

class DownloadThread(QThread):
    """
    A thread class for handling file downloads.
    
    Signals:
        progress_signal: Emits download progress (thread_id, progress_percentage)
        finished_signal: Emits when download is complete (thread_id)
        error_signal: Emits when an error occurs (thread_id, error_message)
    """
    progress_signal = pyqtSignal(str, int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str, str)

    def __init__(self, url: str, save_path: str) -> None:
        """
        Initialize the download thread.

        Args:
            url: The URL to download from
            save_path: The local path to save the file to
        """
        super().__init__()

        self.url: str = url
        self.save_path: str = save_path
        self.download_id: str = str(uuid.uuid4())  # Generate a random UUID.
        self._is_interrupted: bool = False

    def interrupt(self) -> None:
        """Signal the thread to stop downloading."""
        self._is_interrupted = True

    def run(self) -> None:
        """
        Execute the download process in a separate thread.
        Handles the actual file download and emits progress signals.
        """
        try:
            response = requests.get(self.url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            
            with open(self.save_path, 'wb') as f:
                if total_size == 0:
                    if not self._is_interrupted:
                        f.write(response.content)
                else:
                    downloaded = 0
                    for data in response.iter_content(chunk_size=4096):
                        if self._is_interrupted:
                            raise InterruptedError("Download interrupted by user")
                        downloaded += len(data)
                        f.write(data)
                        progress = int((downloaded / total_size) * 100)
                        self.progress_signal.emit(self.download_id, progress)
            
            if not self._is_interrupted:
                self.finished_signal.emit(self.download_id)
            
        except InterruptedError as e:
            self.error_signal.emit(self.download_id, str(e))
            # Clean up partial download
            if os.path.exists(self.save_path):
                os.remove(self.save_path)
        except Exception as e:
            self.error_signal.emit(self.download_id, str(e))

class DownloadWidget(QFrame):
    """
    Widget representing a single download item in the UI.
    Displays the URL, progress bar, and status of the download.
    """

    def __init__(self, url: str, save_path: str) -> None:
        """
        Initialize the download widget.

        Args:
            url: The URL to download from
            save_path: The local path to save the file to
        """
        super().__init__()
        self.url: str = url
        self.save_path: str = save_path
        self.thread: Optional[DownloadThread] = None
        self.is_started: bool = False
        self.is_finished: bool = False
        
        self._setup_ui()
        self._setup_thread()

    def _setup_ui(self) -> None:
        """Set up the UI components of the download widget."""
        layout = QVBoxLayout()
        
        # URL label
        self.url_label = QLabel(f"URL: {self.url}")
        self.url_label.setWordWrap(True)
        layout.addWidget(self.url_label)
        
        # Progress bar and status in horizontal layout
        progress_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.interrupt_button = QPushButton("Interrupt")
        self.interrupt_button.clicked.connect(self.interrupt_download)
        self.interrupt_button.setEnabled(False)
        progress_layout.addWidget(self.interrupt_button)
        
        layout.addLayout(progress_layout)
        
        # Status label
        self.status_label = QLabel("Ready to download")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.setFrameStyle(QFrame.Box | QFrame.Raised)

    def _setup_thread(self) -> None:
        """Initialize the download thread and connect signals."""
        self.thread = DownloadThread(self.url, self.save_path)
        self.thread.progress_signal.connect(self.update_progress)
        self.thread.finished_signal.connect(self.download_finished)
        self.thread.error_signal.connect(self.download_error)
        self.download_id = self.thread.download_id

    def start_download(self) -> None:
        """Start the download if it hasn't been started yet."""
        if not self.is_started and self.thread:
            self.thread.start()
            self.status_label.setText("Downloading...")
            self.is_started = True
            self.interrupt_button.setEnabled(True)

    def interrupt_download(self) -> None:
        """Interrupt the current download."""
        if self.thread and self.is_started and not self.is_finished:
            self.thread.interrupt()
            self.interrupt_button.setEnabled(False)
            self.status_label.setText("Interrupting...")

    def update_progress(self, thread_id: str, progress: int) -> None:
        """
        Update the progress bar value.

        Args:
            thread_id: The ID of the download thread
            progress: The download progress percentage
        """
        if thread_id == self.download_id:
            self.progress_bar.setValue(progress)

    def download_finished(self, thread_id: str) -> None:
        """
        Handle download completion.

        Args:
            thread_id: The ID of the download thread
        """
        if thread_id == self.download_id:
            self.status_label.setText("Complete!")
            self.progress_bar.setValue(100)
            self.is_finished = True
            self.interrupt_button.setEnabled(False)

    def download_error(self, thread_id: str, error_msg: str) -> None:
        """
        Handle download errors.

        Args:
            thread_id: The ID of the download thread
            error_msg: The error message to display
        """
        if thread_id == self.download_id:
            self.status_label.setText(f"Error: {error_msg}")
            self.interrupt_button.setEnabled(False)


class DownloaderApp(QMainWindow):
    """
    Main application window for the multi-threaded file downloader.
    Provides interface for adding and starting downloads.
    """

    def __init__(self) -> None:
        """Initialize the main application window and set up the UI."""
        super().__init__()        
        
        self.downloads: List[DownloadWidget] = []
        self._setup_ui()    

    def _setup_ui(self) -> None:
        """Set up the main UI components."""
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to download")
        
        add_button = QPushButton("Add Download")
        add_button.setFixedWidth(90)
        add_button.clicked.connect(self.add_download)

        # Input layout
        input_layout = QHBoxLayout()
        input_layout.addWidget(self.url_input)
        input_layout.addWidget(add_button)
        
        start_button = QPushButton("Start All Downloads")
        start_button.setFixedWidth(110)
        start_button.clicked.connect(self.start_all_downloads)
        
        interrupt_all_button = QPushButton("Interrupt All")
        interrupt_all_button.setFixedWidth(90)
        interrupt_all_button.clicked.connect(self.interrupt_all_downloads)
        
        clear_button = QPushButton("Clear List")
        clear_button.setFixedWidth(90)
        clear_button.clicked.connect(self.clear_downloads)

        # Buttons layout
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(start_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(interrupt_all_button)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(clear_button)
        
        # Container for download widgets
        self.downloads_container = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_container)
        self.downloads_layout.addStretch()
        
        # Scroll area for downloads
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.downloads_container)

        # Create the main layout.
        layout = QVBoxLayout()
        layout.addLayout(input_layout)        
        layout.addWidget(scroll)
        layout.addLayout(buttons_layout)   

        # Create the central widget.
        central_widget = QWidget()
        central_widget.setLayout(layout)

        # Set up this windows.
        self.setCentralWidget(central_widget) 
        self.setWindowTitle("File Downloader")
        self.setMinimumSize(600, 200)    
        

    def add_download(self) -> None:
        """
        Add a new download to the list without starting it.
        Creates a new DownloadWidget and adds it to the 
        scroll area.
        """
        url = self.url_input.text().strip()
        if not url:
            return
        
        filename = os.path.basename(url.split('?')[0])
        if not filename:
            filename = 'download_' + str(len(self.downloads) + 1)
            
        save_path = filename
        
        download_widget = DownloadWidget(url, save_path)
        self.downloads_layout.insertWidget(len(self.downloads), 
                                           download_widget)
        self.downloads.append(download_widget)
        
        self.url_input.clear()

    def start_all_downloads(self) -> None:
        """Start all downloads that haven't been started yet."""
        for download in self.downloads:
            if not download.is_started:
                download.start_download()

    def interrupt_all_downloads(self) -> None:
        """Interrupt all active downloads."""
        for download in self.downloads:
            if download.is_started and not download.is_finished:
                download.interrupt_download()

    def clear_downloads(self) -> None:
        """
        Clear the downloads list after confirmation.
        Active downloads will be interrupted before clearing.
        """
        if not self.downloads:
            return
            
        reply = QMessageBox.question(
            self,
            'Clear Downloads',
            'Are you sure you want to clear all downloads? Active \
            downloads will be interrupted.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Interrupt active downloads
            self.interrupt_all_downloads()
            
            # Clear the list
            for download in self.downloads:
                self.downloads_layout.removeWidget(download)
                download.deleteLater()
            self.downloads.clear()

def main() -> None:
    """Initialize and run the application."""
    app = QApplication(sys.argv)
    window = DownloaderApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()