import sys
import threading
import os
import time
import hashlib
from socket import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from SeederQThread import UDPClient

class UDPClientGUI(QMainWindow):
    """Seeder window for the P2P client"""
    closed = pyqtSignal() # to tell that window is closed
    
    def __init__(self,tracker_ip,tracker_port):
        super().__init__()
        self.setWindowTitle("Seeder")
        self.setFixedSize(700, 600)
        

        # Create base directory if it doesn't exist
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.resources_dir = os.path.join(self.base_path, "Resources")
        if not os.path.exists(self.resources_dir):
            os.makedirs(self.resources_dir)

        # Client properties
        self.client = None
        self.resources = []
        self.tracker_ip = tracker_ip
        self.tracker_port = tracker_port
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
        
        # Add fields to connection layout
        connection_layout.addRow("Tracker IP:", self.ip_input)
        connection_layout.addRow("Port:", self.port_input)
        
        connection_group.setLayout(connection_layout)
        
        # ===========================================
        # Create splitter for resizable UI sections
        # ===========================================
        splitter = QSplitter(Qt.Vertical)
        
        # ===========================================
        # Top section - Resources
        # ===========================================
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        
        # Resources section
        resources_group = QGroupBox("Resources")
        resources_layout = QVBoxLayout()
        
        # Resources list and controls
        resources_control_layout = QHBoxLayout()
        self.add_resource_button = QPushButton("Add Resource")
        self.remove_resource_button = QPushButton("Remove Selected")
        
        resources_control_layout.addWidget(self.add_resource_button)
        resources_control_layout.addWidget(self.remove_resource_button)
        
        self.resources_list = QListWidget()
        
        resources_layout.addLayout(resources_control_layout)
        resources_layout.addWidget(self.resources_list)
        
        resources_group.setLayout(resources_layout)
        
        # Add to top layout
        top_layout.addWidget(resources_group)
        
        # ===========================================
        # Middle section - Actions
        # ===========================================
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout()
        
        # connect and disconnect buttons
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        
        actions_layout.addWidget(self.connect_button)
        actions_layout.addWidget(self.disconnect_button)
        
        actions_group.setLayout(actions_layout)
        
        # Add to middle layout
        middle_layout.addWidget(actions_group)
        
        # ===========================================
        # Bottom section - Status and Log
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
        
        # Add status and log to bottom layout
        bottom_layout.addWidget(status_group)
        
        # Add widgets to splitter
        splitter.addWidget(top_widget)
        splitter.addWidget(middle_widget)
        splitter.addWidget(bottom_widget)
        
        # Set initial splitter sizes
        splitter.setSizes([200, 100, 300])
        
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
        self.add_resource_button.clicked.connect(self.add_resource)
        self.remove_resource_button.clicked.connect(self.remove_resource)
        
        
        # Initial button state - connect button should be disabled until a resource is added
        self.connect_button.setEnabled(False)

        # Scan resources directory for files
        self.scan_resources_directory()
    
    def log(self, message):
        """Add message to log with timestamp"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        self.log_text.append(f"[{timestamp}] {message}")
        # Scroll to bottom to always show most recent logs
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    def scan_resources_directory(self):
        """Scan the resources directory for files to add to the resources list"""
        try:
            if os.path.exists(self.resources_dir):
                for filename in os.listdir(self.resources_dir):
                    file_path = os.path.join(self.resources_dir, filename)
                    if os.path.isfile(file_path):
                        file_size = os.path.getsize(file_path)
                        resource = f"{filename}&{file_size}"
                        self.resources.append(resource)
                        self.resources_list.addItem(filename)
                
                if len(self.resources) > 0:
                    self.connect_button.setEnabled(True)
                    self.log(f"Found {len(self.resources)} resources in directory")
        except Exception as e:
            self.log(f"Error scanning resources directory: {str(e)}")
    
    def connect_to_tracker(self):
        """Connect to the tracker server"""
        try:
            # Check if resources are available
            if not self.resources:
                self.log("Cannot connect: No resources added")
                QMessageBox.warning(self, "Connection Error", "You must add at least one resource before connecting")
                return
                
            # Get IP and port from input fields
            ip = self.ip_input.text().strip()
            port = int(self.port_input.text().strip())
            
            # Create UDP client
            self.client = UDPClient(ip, port)
            
            self.client.connected.connect(self.update_connection_status)
            self.client.log_message.connect(self.log)
            # Set client resources
            self.client.resources = self.resources

            self.client.start()

            #update gui
            self.update_connection_status(True)
            self.log(f"Connected to tracker at {ip}:{port}")
        except Exception as e:
            # Handle any other errors during connection
            self.log(f"Error connecting to tracker: {str(e)}")
            QMessageBox.warning(self, "Connection Error", f"Failed to connect to tracker: {str(e)}")
     
    
    def disconnect_from_tracker(self):
        """Disconnect from the tracker server"""
        try:
            # Stop any ongoing processes
            if self.client and hasattr(self.client, 'running') and self.client.running:
                self.client.running = False
                self.client.unregister()
            
            # Update UI to show disconnected state
            self.update_connection_status(False)
            self.log("Disconnected from tracker")
            
        except Exception as e:
            # Handle any errors during disconnection
            self.log(f"Error disconnecting from tracker: {str(e)}")
            QMessageBox.warning(self, "Disconnection Error", f"Error during disconnection: {str(e)}")
    
    def add_resource(self):
        """Add a resource to share"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Resource", "", "All Files (*)")
     
        if file_path:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            resource = f"{file_name}&{file_size}"

            # Copy file to current directory if it's not already there
            to_resource_folder = os.path.join(self.base_path, "Resources", file_name)
            if not os.path.exists(to_resource_folder):
                try:
                    #adding file to Resources folder
                    with open(file_path, "rb") as src, open(to_resource_folder, "wb") as dst:
                        dst.write(src.read())
                    self.log(f"Copied {file_name} to current directory")
                except Exception as e:
                    self.log(f"Error copying file: {str(e)}")
                    return
            
            if resource not in self.resources:
                self.resources.append(resource)
                self.resources_list.addItem(file_name)
                self.log(f"Added resource: {file_name} ({file_size} bytes)")
                
                # Enable connect button when at least one resource is added
                if not self.connect_button.isEnabled() and not self.client:
                    self.connect_button.setEnabled(True)
            else:
                self.log(f"Resource {file_name} already added")

    
    def remove_resource(self):
        """Remove selected resource"""
        selected_items = self.resources_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        file_name = item.text()
        
        # Find and remove the resource
        for i, resource in enumerate(self.resources):
            if resource.startswith(file_name):
                del self.resources[i]
                self.log(f"Removed resource: {file_name}")
                break
        
        # Remove from list widget
        self.resources_list.takeItem(self.resources_list.row(item))
        
        # Disable connect button if no resources left
        if len(self.resources) == 0 and not self.client:
            self.connect_button.setEnabled(False)
    @pyqtSlot(bool)
    def update_connection_status(self, connected):
        """Update UI components based on connection status"""
        # Enable/disable buttons based on connection state
        if connected:
            self.connect_button.setEnabled(False)
            self.disconnect_button.setEnabled(True)
            self.add_resource_button.setEnabled(False)
            self.remove_resource_button.setEnabled(False)
            self.status_label.setText("Connected to tracker")
        else:
            # Only enable connect if there are resources
            self.connect_button.setEnabled(len(self.resources) > 0)
            self.disconnect_button.setEnabled(False)
            self.add_resource_button.setEnabled(True)
            self.remove_resource_button.setEnabled(True)
            self.status_label.setText("Not connected to tracker")
            self.client = None
    
    def closeEvent(self, event):
        """Handle window close event to clean up resources"""
        # Clean up any running processes
        try:
            if self.client and hasattr(self.client, 'running') and self.client.running:
                self.client.unregister()
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
    
    # Create and show the main GUI window
    window = UDPClientGUI()
    window.show()
    
    # Start application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()