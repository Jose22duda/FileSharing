# P2P File-Sharing System  (Mickey Mpofu and Joseph Duda)

##  **Project Overview**  

This project implements a **peer-to-peer (P2P) file-sharing system** inspired by BitTorrent. It enables decentralized file sharing among multiple peers without relying on a central server for data transfer. The system uses a **hybrid UDP/TCP protocol architecture** for efficient peer discovery and reliable file transfers.  

###  **Key Features**  
 **Tracker (UDP Server)** – Lightweight coordination for peer discovery and resource listing.  
 **Seeder (TCP Server)** – Hosts complete files and serves chunks to leechers.  
 **Leecher (TCP Client)** – Downloads file chunks in parallel from multiple seeders.  
 **File Integrity Verification** – Uses **SHA-256 hashing** to ensure data correctness.  
 **Parallel Downloads** – Multi-threading for faster file transfers.  
 **User-Friendly GUI** – PyQt5-based interface for easy interaction.  

---

## **System Architecture**  

The system follows a **hybrid P2P model**:  
1. **Centralized Tracker (UDP)** – Maintains a list of active peers and available files.  
2. **Decentralized Data Transfer (TCP)** – Peers (seeders and leechers) communicate directly for file sharing.  


---

##  **How It Works**  

### **1️ Peer Registration**  
- **Seeders** register their files with the tracker via **UDP**.  
- **Leechers** query the tracker to discover available files.  

### **2️ File Download Process**  
1. A **leecher** requests a file from the tracker.  
2. The tracker responds with a list of **seeders** hosting the file.  
3. The leecher connects to multiple seeders via **TCP** to download file chunks in parallel.  
4. Downloaded chunks are verified using **SHA-256 hashes** and reassembled into the complete file.  

### **3️ Dynamic Chunk Handling**  
- Files are split into **smaller chunks** for efficient distribution.  
- Large files use **adaptive chunking** to optimize memory usage.  

---

### **Prerequisites**  
- Python 3.8+  
- PyQt5 (`pip install PyQt5`)  

### **Running the System**  
1. **Start the Tracker (UDP Server)**  
   ```bash
   python tracker.py --host 0.0.0.0 --port 139
    ```
2. **Run a Seeder (Share Files)**
   ```bash
   python seeder.py --tracker-ip localhost --tracker-port 139 --resources /path/to/files
   ```
3. **Launch the Leecher (Download Files via GUI)**
   ```bash
   python leecher.py
   ```
