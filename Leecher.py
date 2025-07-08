import sys
import os
import threading
from socket import *
import time
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QFont, QIcon
from DownloadWorker import DownloadWorker
import Seeder
import SeederGUI

class P2PClientGUI(QMainWindow):

    """Leecher window for the P2P client"""
    # Signal to notify when window is closed
    closed = pyqtSignal()
    def __init__(self,tracker_ip,tracker_port):
        super().__init__()
        self.setWindowTitle("P2P File Sharing Client")
        self.setFixedSize(800, 800)  # Set fixed window size

        # Create the downloads directory if it doesn't exist
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.downloads_dir = os.path.join(self.base_path, "Downloads")
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)


        # Initialize UDP client with tracker address
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
        self.client = Seeder.UDPClient(tracker_ip,tracker_port)

        # Create a Lock object for thread-safe updates to progress bar
        self.lock = threading.Lock()

        # Initialize UI components
        self.init_ui()
        
        # Set initial connection status as disconnected
        self.update_connection_status(False)
        
    def init_ui(self):
        """Initialize all UI components and layouts"""
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # ===========================================
        # Connection Panel - Top section
        # ===========================================
        connection_group = QGroupBox("Tracker Connection")
        connection_layout = QFormLayout()
        
        # Tracker IP and port input fields
        self.ip_input = QLineEdit("localhost")
        self.port_input = QLineEdit("139")
        self.port_input.setFixedWidth(100)
        
        # Connection buttons (Connect/Disconnect)
        button_layout = QHBoxLayout()
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        
        button_layout.addWidget(self.connect_button)
        button_layout.addWidget(self.disconnect_button)
        button_layout.addStretch()  # Push buttons to the left
        
        # Add fields to connection layout
        connection_layout.addRow("Tracker IP:", self.ip_input)
        connection_layout.addRow("Port:", self.port_input)
        connection_layout.addRow("Actions:", button_layout)
        
        connection_group.setLayout(connection_layout)
        
        # ===========================================
        # Create splitter for resizable UI sections
        # ===========================================
        splitter = QSplitter(Qt.Vertical)
        
        # ===========================================
        # Top section - Available files
        # ===========================================
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Available files section
        available_group = QGroupBox("Available Files")
        available_layout = QVBoxLayout()
        
        # File list and controls
        self.refresh_button = QPushButton("Refresh Files")
        self.available_files_list = QListWidget()
        self.download_button = QPushButton("Download Selected")
        self.download_button.setEnabled(False)  # Disabled until a file is selected
        
        available_layout.addWidget(self.refresh_button)
        available_layout.addWidget(self.available_files_list)
        available_layout.addWidget(self.download_button)
        
        available_group.setLayout(available_layout)
        
        # Add to top layout
        top_layout.addWidget(available_group)
        
        # ===========================================
        # Bottom section - Download progress and log
        # ===========================================
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Status and log section
        status_group = QGroupBox("Status and Log")
        status_layout = QVBoxLayout()
        
        self.status_label = QLabel("Not connected to tracker")
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)  # Log is read-only
        
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.log_text)
        
        status_group.setLayout(status_layout)
        
        # Progress bar section
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout()
        
        self.current_file_label = QLabel("No download in progress")
        self.progress_bar = QProgressBar()
        # Set progress bar to have more precise values (0-1000 instead of 0-100)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        
        progress_layout.addWidget(self.current_file_label)
        progress_layout.addWidget(self.progress_bar)
        
        progress_group.setLayout(progress_layout)
        
        # Add status and progress to bottom layout
        bottom_layout.addWidget(status_group)
        bottom_layout.addWidget(progress_group)
        
        # Add widgets to splitter
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes (top gets more space than bottom)
        splitter.setSizes([400, 200])
        
        # Add all components to main layout
        main_layout.addWidget(connection_group)
        main_layout.addWidget(splitter)
        
        # Set main layout
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # ===========================================
        # Connect UI signals to slots (event handlers)
        # ===========================================
        self.connect_button.clicked.connect(self.connect_to_tracker)
        self.disconnect_button.clicked.connect(self.disconnect_from_tracker)
        self.refresh_button.clicked.connect(self.query_available_files)
        self.available_files_list.itemClicked.connect(self.enable_download_button)
        self.download_button.clicked.connect(self.download_selected_file)
    
    def log(self, message):
        """Add message to log with timestamp"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text.append(f"[{timestamp}] {message}")
        # Scroll to bottom to always show most recent logs
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def connect_to_tracker(self):
        """Connect to the tracker server and verify connection"""
        try:
            # Get IP and port from input fields
            ip = self.ip_input.text().strip()
            port = int(self.port_input.text().strip())
            
            # Update client's tracker address
            self.client.tracker_address = (ip, port)
            
            # Test connection by sending CLIENT message
            self.client.socket.sendto(b"CLIENT", self.client.tracker_address)
            self.client.socket.settimeout(5)  # Set timeout for response
            
            try:
                # Wait for response from tracker
                response, _ = self.client.socket.recvfrom(1024)
                if response.decode().strip() == "OK":
                    # Connection successful
                    self.update_connection_status(True)
                    self.log(f"Connected to tracker at {ip}:{port}")
                    # Automatically query available files after connection
                    self.query_available_files()
                else:
                    # Unexpected response
                    self.log(f"Unexpected response from tracker: {response.decode()}")
            except timeout:
                # No response received within timeout period
                self.log("Connection timed out. Tracker not responding.")
                return
            
        except Exception as e:
            # Handle any other errors during connection
            self.log(f"Error connecting to tracker: {str(e)}")
            QMessageBox.warning(self, "Connection Error", f"Failed to connect to tracker: {str(e)}")
        finally:
            # Reset socket timeout regardless of connection success/failure
            self.client.socket.settimeout(None)
    
    def disconnect_from_tracker(self):
        """Disconnect from the tracker server"""
        try:
            # Stop any ongoing processes
            if hasattr(self.client, 'running') and self.client.running:
                self.client.running = False
            
            # Update UI to show disconnected state
            self.update_connection_status(False)
            self.log("Disconnected from tracker")
            
        except Exception as e:
            # Handle any errors during disconnection
            self.log(f"Error disconnecting from tracker: {str(e)}")
            QMessageBox.warning(self, "Disconnection Error", f"Error during disconnection: {str(e)}")
    
    def query_available_files(self):
        """Query tracker for available files in the network"""
        self.log("Querying tracker for available files...")

        try:
            # Send QUERY command to tracker
            self.client.socket.sendto(b"QUERY", self.client.tracker_address)
            # Wait for response with file list
            response, _ = self.client.socket.recvfrom(4096)
            # Process the response
            self.on_query_completed(response.decode())
        except Exception as e:
            # Handle any errors during query
            self.on_query_completed(f"Error querying tracker: {str(e)}")
    
    @pyqtSlot(str)
    def on_query_completed(self, response):
        """Handle query completion and update available files list"""
        self.log("Received file list from tracker")
        
        # Clear the previous file list
        self.available_files_list.clear()
        
        # Parse response and add files to list
        lines = response.strip().split('\n')
        #Build an unordered collection of unique elements.
        unique_files = set()  # Use set to avoid duplicates
        
        for line in lines:
            if not line.strip():
                continue
                
            try:
                # Parse the peer:resources format
                peer_addr, resources = line.split(':', 1)
                for resource in resources.split(','):
                    resource = resource.strip()
                    if resource:
                        # Extract filename from 'filename&size' format
                        if '&' in resource:
                            filename = resource.split('&')[0]
                            unique_files.add(filename)
            except Exception as e:
                # Log parsing errors but continue processing other entries
                self.log(f"Error parsing resource: {line} - {str(e)}")
        
        # Add unique files to the list widget (sorted alphabetically)
        for filename in sorted(unique_files):
            self.available_files_list.addItem(filename)
    
    def enable_download_button(self):
        """Enable download button when a file is selected from the list"""
        self.download_button.setEnabled(True)
    
    def download_selected_file(self):
        """Start downloading the selected file"""
        selected_items = self.available_files_list.selectedItems()
        if not selected_items:
            return
        
        # Get the filename of the selected item
        filename = selected_items[0].text()
        self.log(f"Starting download for {filename}")
        self.current_file_label.setText(f"Downloading: {filename}")
        self.progress_bar.setValue(0)  # Reset progress bar
        
        # Create and start the download worker thread
        self.download_worker = DownloadWorker(self.client, filename)
        # Connect signals to handle progress updates and completion
        self.download_worker.progress_updated.connect(self.update_download_progress)
        self.download_worker.download_completed.connect(self.on_download_completed)
        self.download_worker.log_message.connect(self.log)
        self.download_worker.start()
    
    @pyqtSlot(int, int)
    def update_download_progress(self, chunk_id, progress):
        """Update download progress for a specific chunk"""
        # Thread-safe update of progress bar
        with self.lock:
            if progress == -1:
                # Error in this chunk, but continue with others
                pass
            else:
                # Update progress bar (ensure we don't exceed maximum)
                new_value = min(progress, 1000)
                self.progress_bar.setValue(new_value)
    
    @pyqtSlot(bool, str)
    def on_download_completed(self, success, message):
        """Handle download completion event"""
        if success:
            # Set progress bar to 100% on success
            self.progress_bar.setValue(1000)
            self.log(message)
            try:
                filename = message.split("Downloaded Complete :")[1].strip()
            except:
                filename = "downloaded file"
              
            # Ask user if they want to seed this file
            reply = QMessageBox.question(self, "Download Complete", 
                                         f"Download complete: {filename}\n\nWould you like to share this file as a seeder?",
                                         QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # Move file from Downloads to Resources directory
                downloaded_path = os.path.join(self.downloads_dir, filename)
                resource_path = os.path.join(self.base_path, "Resources", filename)
                
                try:
                    # Create Resources directory if it doesn't exist
                    resources_dir = os.path.join(self.base_path, "Resources")
                    if not os.path.exists(resources_dir):
                        os.makedirs(resources_dir)
                    
                    # Copy file to Resources directory if it exists
                    if os.path.exists(downloaded_path):
                        with open(downloaded_path, "rb") as src, open(resource_path, "wb") as dst:
                            dst.write(src.read())
                        self.log(f"File {filename} prepared for seeding")
                        
                        # Close this window
                        self.log("Switching to seeder mode...")
                        self.close()
                        self.parent.hide()
                        
                        # Open seeder window
                        self.seeder_window = SeederGUI.UDPClientGUI(self.tracker_ip, self.tracker_port)
                        self.seeder_window.closed.connect(self.parent.show)  # Show main menu when seeder is closed
                        self.seeder_window.show()
                    else:
                        self.log(f"Error: Could not find downloaded file at {downloaded_path}")
                        QMessageBox.warning(self, "Error", f"Could not find downloaded file at {downloaded_path}")
                except Exception as e:
                    self.log(f"Error preparing file for seeding: {str(e)}")
                    QMessageBox.warning(self, "Error", f"Error preparing file for seeding: {str(e)}")
        else:
            # Reset progress bar on failure
            self.progress_bar.setValue(0)
            self.log(f"Download failed: {message}")
            QMessageBox.warning(self, "Download Failed", message)
        
        # Update status label
        self.current_file_label.setText("No download in progress")
    
    def update_connection_status(self, connected):
        """Update UI components based on connection status"""
        # Enable/disable buttons based on connection state
        self.connect_button.setEnabled(not connected)
        self.disconnect_button.setEnabled(connected)
        self.refresh_button.setEnabled(connected)
        
        # Update status label
        if connected:
            self.status_label.setText("Connected to tracker")
        else:
            self.status_label.setText("Not connected to tracker")
            # Clear file list when disconnected
            self.available_files_list.clear()
            self.download_button.setEnabled(False)
    
    def closeEvent(self, event):
        """Handle window close event to clean up resources"""
        # Clean up any running processes
        try:
            if hasattr(self.client, 'running') and self.client.running:
                self.client.running = False
        except:
            pass
        # Emit closed signal
        self.closed.emit()
        event.accept()  # Allow window to close

def main():
    """Main entry point for the application"""
    # Create PyQt application
    app = QApplication(sys.argv)
    
    # Set default styling for a consistent look
    app.setStyle("Fusion")
    
    # Create P2P client with default tracker address
    tracker_ip = "196.42.85.37"
    tracker_port = 139
    client = Seeder.UDPClient(tracker_ip, tracker_port)
    
    # Create and show the main GUI window
    window = P2PClientGUI(tracker_ip,tracker_port)
    window.show()
    
    # Start application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()