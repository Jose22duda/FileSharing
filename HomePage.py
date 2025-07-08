import sys
import os
import threading
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from SeederQThread import UDPClient
from DownloadWorker import DownloadWorker
import SeederGUI
import Leecher

class HomePage(QMainWindow):
    """Main GUI window that allows users to choose between seeder and leecher roles"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("P2P File Sharing")
        self.setFixedSize(400, 300)
        
        # Create base directories if they don't exist
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.resources_dir = os.path.join(self.base_path, "Resources")
        self.downloads_dir = os.path.join(self.base_path, "Downloads")
        
        
        # Create directories if they don't exist
        for directory in [self.resources_dir, self.downloads_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        # Initialize UI components
        self.init_ui()
        
    def init_ui(self):
        """Initialize the main selection UI"""
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Add title label
        title_label = QLabel("P2P File Sharing")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # Add description
        desc_label = QLabel("Choose your role in the P2P network:")
        desc_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(desc_label)
        
        # Add spacer
        main_layout.addSpacing(20)
        
        # Create seeder button
        self.seeder_button = QPushButton("Seeder Mode")
        self.seeder_button.setMinimumHeight(50)
        self.seeder_button.setToolTip("Share files with others")
        main_layout.addWidget(self.seeder_button)
        
        # Create leecher button
        self.leecher_button = QPushButton("Leecher Mode")
        self.leecher_button.setMinimumHeight(50)
        self.leecher_button.setToolTip("Download files from the network")
        main_layout.addWidget(self.leecher_button)
        
        # Add spacer
        main_layout.addSpacing(20)
        
        # Add tracker settings
        tracker_group = QGroupBox("Tracker Settings")
        tracker_layout = QFormLayout()
        
        self.ip_input = QLineEdit("localhost")
        self.port_input = QLineEdit("139")
        
        tracker_layout.addRow("Tracker IP:", self.ip_input)
        tracker_layout.addRow("Port:", self.port_input)
        
        tracker_group.setLayout(tracker_layout)
        main_layout.addWidget(tracker_group)
        
        # Add exit button
        self.exit_button = QPushButton("Exit")
        main_layout.addWidget(self.exit_button)
        
        # Set main layout
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Connect buttons to functions
        self.seeder_button.clicked.connect(self.open_seeder)
        self.leecher_button.clicked.connect(self.open_leecher)
        self.exit_button.clicked.connect(self.close)
        
    def open_seeder(self):
        """Open the seeder window"""
        tracker_ip = self.ip_input.text().strip()
        tracker_port = int(self.port_input.text().strip())
        
        # Hide this window
        self.hide()
        
        # Create and show the seeder window
        self.seeder_window = SeederGUI.UDPClientGUI(tracker_ip, tracker_port)
        self.seeder_window.closed.connect(self.show)  # Show this window when seeder is closed
        self.seeder_window.show()
        
    def open_leecher(self):
        """Open the leecher window"""
        tracker_ip = self.ip_input.text().strip()
        tracker_port = int(self.port_input.text().strip())
        
        # Hide this window
        self.hide()
        
        # Create and show the leecher window
        self.leecher_window = Leecher.P2PClientGUI(tracker_ip, tracker_port)
        self.leecher_window.parent = self
        self.leecher_window.closed.connect(self.show)
        self.leecher_window.show()

def main():
    """Main entry point for the application"""
    # Create PyQt application
    app = QApplication(sys.argv)
    
    # Set default styling for a consistent look
    app.setStyle("Fusion")
    
    # Create and show the main GUI window
    window = HomePage()
    window.show()
    
    # Start application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()