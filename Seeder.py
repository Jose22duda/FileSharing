import sys
import threading
import os
import time
import hashlib  # Added for file integrity verification
from socket import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class UDPClient:
    BUFFER_SIZE = 4096
    resources = []  # List to store resources (file names with extensions)
    NoResource = False

    def __init__(self, tracker_host, tracker_port,files =None):
        """ Initialize the UDP client with tracker details and resources to register """
        try:
            self.tracker_address = (tracker_host, tracker_port)
            self.socket = socket(AF_INET, SOCK_DGRAM)
            self.running = False
            self.MAX_CHUNKS_PER_SEEDER_DOWNLOAD = 200
            if (files is not None):
                for file in files:
                    self.resources.append(file)
                    print(files)
            else:
                # Get the current directory (where the Python script is located)
                current_directory = os.path.dirname(os.path.realpath(__file__))
                resources_folder = os.path.join(current_directory, 'Resources')
                
                if not os.path.exists(resources_folder):
                    print(f"[ERROR] Resources folder does not exist: {resources_folder}")
                    return

                # Loop through all files in the directory and add them to the resources list
                for file in os.listdir(resources_folder):
                    if os.path.isfile(os.path.join(resources_folder, file)):  # Check if it's a file
                        file_size = f"&{os.stat(os.path.join(resources_folder, file)).st_size}"
                        self.resources.append(file + file_size)

        except Exception as e:
            print(f"[ERROR] Failed to initialize UDP client: {e}")

    def register(self):
        """ Register the client with the tracker """
        try:
            message = f"REGISTER {','.join(self.resources)}"  # Create the register message  add each element like this ",element"
            self.socket.sendto(message.encode(), self.tracker_address)   # Send message to tracker

            # Receive the response from the tracker
            response, address = self.socket.recvfrom(1024)
            response  = response.decode()
            if response.startswith("OK"):
                print("Server:", response.decode())
                
                # Start the Alive thread
                self.running = True
                self.alive_thread = threading.Thread(target=self.send_Status, daemon=True)
                self.alive_thread.start()

                self.server_thread = threading.Thread(target= self.waitingForTrackerMessage, daemon = True)
                self.server_thread.start()

                # self.waitingForTrackerMessage()
            elif response.startswith("No Resources"):
                print("[+] You did not prived Resources\n[+] Add files to share in you Resource folder")
            elif response.startswith("Message Format Incorrect"):
                print("[+] message format is incorrect")
        except Exception as e:
            print(f"[ERROR] Failed to register with the tracker: {e}")
            

    
    def waitingForTrackerMessage(self):
        """ Wait for and process messages from the tracker """
        try:
            while self.running:
                response, address = self.socket.recvfrom(1024)
                response = response.decode()
                
                if response.startswith("SET SERVER"):
                    message_m = response.split("@")[1]
                    self.setUPTcpServer(message_m)

                elif response.startswith("UNREGISTERED"):
                    print("You have been unregistered as a Seeder by the Tracker")
                    self.running = False

        except Exception as e:
            self.running = False
            print(f"[ERROR] Failed to process tracker message: {e}")
    
    def setUPTcpServer(self, message):
        """ Set up a TCP server for file transfer based on tracker message """
        try:
            # Parse the server address for TCP communication
            response = message.split(":")
            server_address = (response[0], int(response[1]))

            # Establish a TCP server for file transfer
            TCP_server_socket = socket(AF_INET, SOCK_STREAM)
            TCP_server_socket.bind(server_address)
            TCP_server_socket.listen(1)
            print(f"[*] Listening on port {response}...")

            conn, addr = TCP_server_socket.accept()   # Accept incoming connection
            print(f"[+] Connection established with {addr}")

            # Get total number of chunks
            number_of_chunks = int(conn.recv(self.BUFFER_SIZE).decode())
            conn.send("OK".encode())
            print(f"[*] There are total of {number_of_chunks} number of chunks that should be sent by all seeders")

            # Receive the requested file details from the client
            base_path = os.path.dirname(os.path.abspath(__file__))
            response = str(conn.recv(self.BUFFER_SIZE).decode()).split(":")
            
            filename = os.path.join(base_path, "Resources", response[0])
            chunk_size = int(response[1])
            chunk_id = int(response[2])

            print(f"[*] Chunk ID: {response[2]} requested.")
            print(f"[*] Size of chunk: {response[1]} bytes")
            print(f"[*] Client requested chunk of the following file {response[0]}")
            
            # Check if the file exists and send it if available
            if not os.path.exists(filename):
                print(f"[ERROR] File '{filename}' not found.")
                conn.send(b"File Not Found")  # Notify client
            else:
                with open(filename, "rb") as f:
                    filesize = os.stat(filename).st_size
                    # Calculate chunk size dynamically
                    file_size = os.path.getsize(filename)
                    chunk_sizes = [file_size // number_of_chunks] * number_of_chunks
                    
                    # Adjust last chunk to handle remainder
                    chunk_sizes[-1] += file_size % number_of_chunks
                    
                    # Calculate start and end positions for the specific chunk
                    start_pos = sum(chunk_sizes[:chunk_id])
                    chunk_size = chunk_sizes[chunk_id]
                    
                    # Seek to the correct position
                    f.seek(start_pos)

                    # Handle large chunks by splitting them if needed
                    if (chunk_size > 1024 * 1024 * 100):  # if file > 100MB
                        message = "SPLIT CHUNK"
                        conn.send(message.encode())
                        message = conn.recv(self.BUFFER_SIZE).decode()
                        
                        print(f"[*] Leecher response to SPLIT CHUNK?: {message}")
                        print(f"[*] Splitting chunks...")
                        
                        # Calculate smaller chunk sizes
                        small_chunk_sizes = [chunk_size // self.MAX_CHUNKS_PER_SEEDER_DOWNLOAD] * self.MAX_CHUNKS_PER_SEEDER_DOWNLOAD
                        small_chunk_sizes[-1] += chunk_size % self.MAX_CHUNKS_PER_SEEDER_DOWNLOAD
                        count = 0

                        chunk_hash = None
                        print(f"[*] Preparing to send small chunks")
                        
                        while True:
                            # Check if this is the last chunk
                            if count == len(small_chunk_sizes):
                                conn.send("DONE:".encode())
                                break

                            chunk = f.read(small_chunk_sizes[count])

                            if not chunk:  # End of file
                                conn.send("DONE:".encode())
                                break

                            # Sending chunk size and chunk ID
                            mes = f"{small_chunk_sizes[count]}:{count}"
                            conn.send(mes.encode())
                            print(f"Sending chunk size: {len(chunk)}")

                            # Confirmation message received
                            confirmation = conn.recv(1024)

                            # Generate hash for the chunk
                            chunk_hash = self.generate_chunk_hash(chunk)
                            print(f"Sending hash: {chunk_hash}")

                            # Send the chunk hash followed by the chunk data
                            conn.send(f"{chunk_hash}:".encode() + chunk)
                            print(f"[+] Small chunk {count} sent.")
                            count += 1
                            
                            # Pause briefly between chunks
                            time.sleep(0.05)
                    
                    else:
                        # Send the entire chunk at once for smaller files
                        message = "SEND WHOLE CHUNK"
                        conn.send(message.encode())
                        
                        # Read exactly the chunk we want
                        chunk = f.read(chunk_size)
                        
                        # Generate hash for the chunk
                        chunk_hash = self.generate_chunk_hash(chunk)

                        # Send the chunk hash followed by the chunk data
                        conn.send(f"{chunk_hash}:".encode() + chunk)

            print(f"[+] Chunk ID: {chunk_id} chunk was sent")
            TCP_server_socket.close()
            conn.close()
            # self.waitingForTrackerMessage()
        except Exception as e:
            print(f"[ERROR] Failed to set up TCP server: {e}")
    
    def unregister(self):
        """ Unregister the client from the tracker """
        try:
            # make sute it has sent it last alive message  before unregister
            self.socket.sendto(b"UNREGISTER", self.tracker_address)
            # make sure that threads have stopped running 
            self.server_thread.join()
            self.alive_thread.join()
            
        except Exception as e:
            print(f"[ERROR] Failed to unregister from tracker: {e}")
    
    def query_peers(self):
        """ Query the tracker for active peers """
        try:
            self.socket.sendto(b"QUERY", self.tracker_address)
            response, _ = self.socket.recvfrom(4096)
            print("Active Peers:\n", response.decode())
        except Exception as e:
            print(f"[ERROR] Failed to query peers from tracker: {e}")
    
    def send_Status(self):
        """ Function to send Alive messages periodically """
        try:
            while self.running:
                self.socket.sendto(b"ALIVE!", self.tracker_address)
                time.sleep(1)  # Send a message every second
        except Exception as e:
            print(f"[ERROR] Failed to send Alive message: {e}")
    
    def generate_chunk_hash(self, chunk_data):
        """Generate SHA-256 hash for a chunk of data"""
        try:
            sha256_hash = hashlib.sha256()
            sha256_hash.update(chunk_data)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"[ERROR] Failed to generate chunk hash: {e}")
            return None
    

def main():
    try:
        tracker_ip = "196.42.85.37"
        tracker_port = 139
        peer = UDPClient(tracker_ip, tracker_port)
      
        while True:
            cmd = input("Enter command (query/unregister/connect/exit): ").strip().lower()
            if cmd == "query":
                peer.query_peers()
            elif cmd == "unregister":
                peer.unregister()
            elif cmd == "connect":
                peer.register()
            elif cmd == "exit":
                peer.unregister()
                peer.socket.close()
                break
    except Exception as e:
        print(f"[ERROR] An error occurred in the main function: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
