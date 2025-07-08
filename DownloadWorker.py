import os
import threading
import hashlib
from socket import *
from PyQt5.QtCore import *

class DownloadWorker(QThread):
    """Worker thread to handle file downloads without blocking the GUI"""
    # Define signals for communicating with the main thread
    progress_updated = pyqtSignal(int, int)  # chunk_id, progress_percent
    download_completed = pyqtSignal(bool, str)  # success, message
    log_message = pyqtSignal(str)  # Log message for status updates
    chunkLock = threading.Lock()
    
    def __init__(self, client, filename):
        super().__init__()
        self.client = client  # Reference to the main client object
        self.filename = filename  # File to be downloaded
        self.MAX_CHUNKS_PER_SEEDER_DOWNLOAD = 200  # Maximum number of small chunks per seeder
        self.progress_num = 0  # Tracks overall download progress
        self.progresss_lock = threading.Lock()  # Thread-safe progress updates

        # Create the downloads directory if it doesn't exist
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.downloads_dir = os.path.join(self.base_path, "Downloads")
        if not os.path.exists(self.downloads_dir):
            os.makedirs(self.downloads_dir)


    def updatProgressNum(self, num):
        """Thread-safe method to update progress counter and return new value"""
        with self.progresss_lock:
            self.progress_num += num
            return self.progress_num
            
    def resetProgressNum(self):
        """Thread-safe method to reset progress counter"""
        with self.progresss_lock:
            self.progress_num = 0
        
    def run(self):
        """Main download process that runs when thread is started"""
        try:
            # Step 1: Send GET request to tracker to find peers with the file
            message = "GET " + self.filename
            self.client.socket.sendto(message.encode(), self.client.tracker_address)
            response, _ = self.client.socket.recvfrom(4096)
            response = response.decode()
            
            # Check if file exists on any peer
            if response.startswith("Not Found"):
                self.log_message.emit("[ERROR] No peer has the file you requested")
                self.download_completed.emit(False, "File not found")
                return
            
            # Step 2: Parse response from tracker
            response = response.split("/")
            addresses_text = response[0]  # List of peer addresses
            filesize = int(response[1])  # Total file size in bytes
            
            self.log_message.emit(f"[INFO] Found peers with the file. File size: {filesize} bytes")
            
            # Parse list of peer addresses
            addresses = addresses_text.strip().split("\n")
            # Remove any empty entries
            addresses = [addr for addr in addresses if addr.strip()]
            
            # Step 3: Calculate chunk sizes for distribution across peers
            num_chunks = len(addresses)
            # Divide file evenly among peers
            chunk_sizes = [filesize // num_chunks] * num_chunks
            # Add remainder to last chunk
            chunk_sizes[-1] += filesize % num_chunks
            
            # Dictionary to store downloaded chunks by chunk_id
            chunks = {}
            
            # Step 4: Create threads for parallel downloading from multiple peers
            threads = []
            self.log_message.emit(f"[INFO] Starting download from {num_chunks} peers")
            
            # Create and start a thread for each peer
            for i, address in enumerate(addresses):
                if not address.strip():  # Skip empty addresses
                    continue
                
                thread = threading.Thread(
                    target=self.download_chunk_with_progress,
                    args=(address, self.filename, chunk_sizes[i], i, num_chunks, chunks, filesize, self.client.BUFFER_SIZE),
                    daemon=True
                )
                threads.append(thread)
                thread.start()
            
            # Wait for all download threads to complete
            for thread in threads:
                thread.join()

            # Reset progress tracker for potential future downloads
            self.resetProgressNum()
            
            # Step 5: Verify all chunks were received successfully
            if len(chunks) != num_chunks:
                self.log_message.emit(f"[WARNING] Only received {len(chunks)}/{num_chunks} chunks")
                if len(chunks) == 0:
                    self.download_completed.emit(False, "Download failed - no chunks received")
                    return
            
            # Step 6: Assemble the complete file from chunks
            self.log_message.emit("[INFO] Assembling file from chunks")
            output_file = os.path.join(self.downloads_dir,self.filename)
            with open(output_file, "wb") as f:
                # Write chunks in correct order
                for i in range(num_chunks):
                    if i in chunks:
                        f.write(chunks[i])
            
            # Step 7: Notify successful completion
            self.log_message.emit(f"[SUCCESS] File received successfully and saved to {output_file}")
            self.download_completed.emit(True, f"Downloaded Complete :{self.filename}")
            
        except Exception as e:
            # Handle any exceptions during the download process
            self.log_message.emit(f"[ERROR] Download failed: {str(e)}")
            self.download_completed.emit(False, f"Download failed: {str(e)}")

    def generate_chunk_hash(self, chunk_data):
        """Generate SHA-256 hash for a chunk of data for integrity verification"""
        sha256_hash = hashlib.sha256()
        sha256_hash.update(chunk_data)
        return sha256_hash.hexdigest()
    
    def download_chunk_with_progress(self, address, filename, chunk_size, chunk_id, num_chunks, chunks, filesize, buffer_size=4096):
        """Download a specific chunk from a peer with progress tracking and integrity checking"""
        try:
            # Step 1: Parse peer address
            peer = address.split(":")
            ip, port = peer[0], int(peer[1])
            
            self.log_message.emit(f"[INFO] Connecting to peer {ip}:{port} for chunk {chunk_id}")
            
            # Step 2: Connect to the peer
            client_socket = socket(AF_INET, SOCK_STREAM)
            client_socket.connect((ip, port))
            
            # Step 3: Send number of chunks (initial handshake)
            client_socket.send(str(num_chunks).encode())
            client_socket.recv(buffer_size)  # Wait for acknowledgment
            
            # Step 4: Request specific chunk
            request = f"{filename}:{chunk_size}:{chunk_id}"
            client_socket.send(request.encode())

            # Step 5: Check if this chunk needs to be split into smaller pieces
            message = client_socket.recv(buffer_size)
            message = message.decode()
            
            # Handle large chunks that need to be split
            if message.startswith("SPLIT CHUNK"):
                message = "SPLIT"
                client_socket.send(message.encode())  # Acknowledge split mode
                # Initialize array to store small chunks
                small_chunks = [None] * self.MAX_CHUNKS_PER_SEEDER_DOWNLOAD
               
                # Step 5a: Download multiple small chunks that make up a large chunk
                while True:
                    # Receive size of the next chunk and chunk ID
                    message = client_socket.recv(1024).decode()
                    if message.startswith("DONE"):
                        # All small chunks received
                        self.log_message.emit(f"[+] All small chunks of chunk {chunk_id} have been received")
                        break
                        
                    # Parse small chunk metadata  
                    message_parts = message.split(":")
                    next_chunk_size = int(message_parts[0])
                    small_chunk_id = int(message_parts[1])
                    client_socket.send("RECEIVED:CHUNK SIZE:CHUNK ID".encode())  # Acknowledge receipt

                    # Receive chunk data with hash   
                    data = client_socket.recv(next_chunk_size + 70)  # 70 extra bytes for the hash prefix

                    # Update progress bar
                    value_for_progress_bar = int((self.updatProgressNum(next_chunk_size)/filesize)*1000)
                    self.progress_updated.emit(chunk_id, value_for_progress_bar)
                    
                    # Parse data: hash and actual chunk content
                    parts = data.split(b":", 1)
                    
                    if len(parts) == 2:
                        received_hash = parts[0].decode()  # Hash sent by peer
                        chunk = parts[1]  # Actual chunk data
                        
                        self.log_message.emit(f"[*] size of small chunk {small_chunk_id} is : {len(chunk)}")
                        
                        # Verify chunk integrity using hash
                        calculated_hash = self.generate_chunk_hash(chunk)
                        
                        if calculated_hash == received_hash:
                            # Hash verification successful
                            small_chunks[small_chunk_id] = chunk
                            self.log_message.emit(f"[INFO] small Chunk {small_chunk_id} received and verified length is ({len(chunk)} bytes)")
                        else:
                            # Hash verification failed - chunk corrupted
                            self.log_message.emit(f"Integrity check failed for small chunk {small_chunk_id}!")
                            self.log_message.emit(f"Expected: {received_hash}")
                            self.log_message.emit(f"Got: {calculated_hash}")
                            # Update progress to show error
                            self.progress_updated.emit(chunk_id, -1)  # -1 indicates error

                # Combine all small chunks into one large chunk
                with self.chunkLock:
                    chunks[chunk_id] = b"".join(small_chunks)
            else:
                # Step 5b: Download a single chunk directly (no splitting needed)
                data = client_socket.recv(chunk_size + 70)  # Extra bytes for the hash prefix
                
                # Parse data: hash and actual chunk content
                parts = data.split(b":", 1)
                if len(parts) == 2:
                    received_hash = parts[0].decode()  # Hash sent by peer
                    chunk = parts[1]  # Actual chunk data
                    
                    # Update progress bar
                    value_for_progress_bar = int((self.updatProgressNum(chunk_size)/filesize)*1000)
                    self.progress_updated.emit(chunk_id, value_for_progress_bar)
                    
                    # Verify chunk integrity using hash
                    calculated_hash = self.generate_chunk_hash(chunk)
                    
                    if calculated_hash == received_hash:
                        # Hash verification successful
                        with self.chunkLock:
                            chunks[chunk_id] = chunk
                        self.log_message.emit(f"[INFO] Chunk {chunk_id} received and verified ({len(chunk)} bytes)")
                    else:
                        # Hash verification failed - chunk corrupted
                        self.log_message.emit(f"[ERROR] Integrity check failed for chunk {chunk_id}!")
                        self.log_message.emit(f"Expected: {received_hash}")
                        self.log_message.emit(f"Got: {calculated_hash}")
                        # Update progress to show error
                        self.progress_updated.emit(chunk_id, -1)  # -1 indicates error

            # Step 6: Close connection to peer
            client_socket.close()
        
        except Exception as e:
            # Handle any errors during chunk download
            self.log_message.emit(f"[ERROR] Failed to download chunk {chunk_id}: {str(e)}")
            # Update progress to show error
            self.progress_updated.emit(chunk_id, -1)  # -1 indicates error
