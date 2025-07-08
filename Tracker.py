from socket import *
import time
import threading


class Tracker:
    def __init__(self, host="0.0.0.0", port=139):
        """Initialize the tracker server."""
        self.server_address = (host, port)
        self.resourceLock = threading.Lock()
        self.clients = {}  # Dictionary to store {client_address: resources}
        self.tracker_socket = socket(AF_INET, SOCK_DGRAM)
        self.tracker_socket.bind(self.server_address)
        print(f"Tracker started on {host}:{port}")
        
        # Dictionary to store the last received time for each client (client address as key)
        self.clients_last_seen = {}
        self.no_longer_seeder = []
        
        # Start the timeout checking thread
        self.timeout_thread = threading.Thread(target=self.check_for_timeouts, daemon=True)
        self.timeout_thread.start()

    def handle_client(self):
        """Main loop to handle client messages."""
        while True:
            data, addr = self.tracker_socket.recvfrom(1024)          
            message = data.decode().strip()

            if message.startswith("REGISTER"):
                self.handle_register(addr, message)            
                current_time = time.time()
                self.clients_last_seen[addr] = current_time
              
            elif message.startswith("QUERY"):
                self.handle_query(addr)
            elif message.startswith("UPDATE"):
                self.handle_updat(addr,message)

            elif message.startswith("UNREGISTER"):
                self.handle_unregister(addr)

            elif message.startswith("CLIENT"):
                self.handle_client_check(addr)

            elif message.startswith("GET"):
                self.handle_get(addr, message)
                
            elif message.startswith("ALIVE"):
                self.handle_Status(addr, message)

    def check_for_timeouts(self):
        """Check and remove timed-out clients."""
        TIMEOUT = 10  # Timeout for client activity (in seconds)
        
        while True:
            current_time = time.time()
            to_remove = []

            # Check for clients that have timed out
            for client, last_seen in self.clients_last_seen.items():
                if client in self.no_longer_seeder:
                    continue
                if current_time - last_seen > TIMEOUT:
                    print(f"Peer {client} has timed out.")
                    to_remove.append(client)

            # Remove timed-out clients from the clients and clients_last_seen dictionaries
            for client in to_remove:
                del self.clients_last_seen[client]
                with self.resourceLock:
                    if client in self.clients:
                        #in case client is unregistered bore thread could remove it
                        del self.clients[client]

            # Sleep for a while before checking again
            time.sleep(3)

    def handle_register(self, addr, message):
        """Handle client registration."""
        splitMessage = message.split(" ", 1)
        if len(splitMessage) == 2:
            resources = splitMessage[1]
            with self.resourceLock:
                self.clients[addr] = resources.split(",")  # Store resources as a list
                print(f"Registered: {addr} - Resources: {self.clients[addr]}")
            self.tracker_socket.sendto("OK".encode(), addr)

        elif len(splitMessage) == 1:
            self.tracker_socket.sendto("No Resources".encode(), addr)
        else:
            self.tracker_socket.sendto("Message Format Incorrect".encode(), addr)


    def handle_query(self, addr):
        """Handle client query for available resources."""
        # response = "\n".join([f"{peer}: {', '.join(res)}" for peer, & res in self.clients.items()])
        response = "\n"
        for peer, res in self.clients.items():
            response += f"{peer}: "
            for name_size in res:
                response += f",{name_size}"

        self.tracker_socket.sendto(response.encode(), addr)

    def handle_unregister(self, addr):
        """Handle client unregistration."""
        with self.resourceLock:
            if addr in self.clients:
                if addr not in self.no_longer_seeder:
                    self.no_longer_seeder.append(addr)
                del self.clients[addr]
                print(f"Unregistered: {addr}")
        self.tracker_socket.sendto("UNREGISTERED".encode(), addr)  # Fixed missing encode()

    def handle_client_check(self, addr):
        """Handle client connection check."""
        print(f"Client {addr} is connected to server")
        self.tracker_socket.sendto("OK".encode(), addr)

    def handle_get(self, addr, message):
        """Handle file/resource requests from clients."""
        _, filename = message.split(" ", 1)
        
        response = "\n"
        found = False
        size = ""
        
        # Check if any client has the requested file/resource
        for key, value in self.clients.items():
            for mydata in value:
                resource = mydata.split("&")
                if filename in resource:
                    response += f"{key[0]}:{key[1]}\n"
                    if not found:
                        size = resource[1]
                        found = True
                    break

        if not found:
            response = "Not Found"
        else:
            # Send the addresses of clients that have the file/resource
            peer_addresses = response.strip().split("\n")
            for address in peer_addresses:
                address = address.split(":") 
                mes = f"SET SERVER@{address[0]}:{address[1]}"
                ip = address[0]
                port = int(address[1])
                # Send to seeder who has the file
                self.tracker_socket.sendto(mes.encode(), (ip, port))

            # Send the file size to leecher
            response += "/" + size
            
        self.tracker_socket.sendto(response.encode(), addr)
        
    def handle_Status(self, addr, message):
        """Handle status updates from clients."""
        if addr in self.clients:
            self.clients_last_seen[addr] = time.time()
            # print(f"Client {addr} is still connected to server/{message}")  
        # else:
        #     self.tracker_socket.send("UNKNOWN SEEDER:REGISTER AS SEEDER".encode(),addr)

    def handle_updat(self,addr,message):
        """Handle UPDATE resources"""
        cmd, resources = message.split(" ", 1)
        self.clients[addr] = resources.split(",")  # Store resources as a list
        print(f"Seeder: {addr} - UPDATE Resources: {self.clients[addr]}")
        self.tracker_socket.sendto("UPDATED".encode(), addr)



def main():
    """Start the tracker server and handle client connections."""
    server = Tracker()
    server.handle_client()

    try:
        while True:
            pass  # Keep the server running
    except KeyboardInterrupt:
        print("\nTracker shutting down.")


if __name__ == "__main__":
    main()