"""
NetworkSpeedTest_Server.py

Implements the SpeedTestServer class, which:
1) Periodically sends broadcast offers to BROADCAST_IP:DEFAULT_UDP_PORT on an interval.
2) Uses ephemeral ports for actual data transfer (TCP & UDP).
3) Accepts client requests and sends dummy data to fulfill them (in file size).
"""

from Constants import *
import socket
import struct
import threading
import time
import sys

class SpeedTestServer:
    def __init__(self):
        """
        Initialize the server:
         - Determine an IP address to advertise (if needed).
         - Acquire ephemeral UDP & TCP ports for data transfer.
         - Create sockets for broadcasting, UDP requests and TCP requests.
        """
        # Discover the local IP address for reference or logging
        self.server_ip = self.get_own_ip()

        # Allocate ephemeral ports for our data connections
        self.server_udp_port = self.get_free_port()
        self.server_tcp_port = self.get_free_port()

        # Create a socket for broadcasting offer packets and enable broadcast
        self.udp_broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.udp_broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_broadcast_socket.settimeout(0.5) 

        # Create a UDP socket to receive client requests on ephemeral port
        self.udp_request_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_request_socket.bind(("0.0.0.0", self.server_udp_port))
        self.udp_request_socket.settimeout(0.5)

        # Create a TCP socket to listen for client connections on ephemeral port
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.bind(("0.0.0.0", self.server_tcp_port))
        self.tcp_server_socket.listen(5)
        self.tcp_server_socket.settimeout(0.5)

        self.running = True  # Control flag for shutting down

        print(f"{GREEN}Server started, listening on IP address {self.server_ip}{RESET}")

    def get_own_ip(self):
        """
        Discovers the server's IP by opening a dummy connection to a known public address.
        Fallback to 172.1.0.4 if that fails.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to 8.8.8.8:80 just to force the OS to pick an interface
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
        except Exception:
            ip = "172.1.0.4"
        finally:
            sock.close()
        return ip

    def get_free_port(self):
        """
        Ask the OS for an ephemeral TCP port by binding to (0.0.0.0, 0).
        Then close that socket and return the port number.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("0.0.0.0", 0))
        port = s.getsockname()[1]
        s.close()
        return port

    def start(self):
        """
        Launch three threads:
         1) broadcast_offers() - sends periodic offers to BROADCAST_IP:DEFAULT_UDP_PORT.
         2) listen_tcp()       - accepts TCP connections on ephemeral port.
         3) listen_udp_requests() - receives UDP requests on ephemeral port.
        """
        # Use daemon threads so they close if main thread exits
        threading.Thread(target=self.broadcast_offers, daemon=True).start()
        threading.Thread(target=self.listen_tcp, daemon=True).start()
        threading.Thread(target=self.listen_udp_requests, daemon=True).start()

        try:
            # Keep main thread alive until a KeyboardInterrupt
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"{RED}Server shutting down...{RESET}")
            self.running = False

    def broadcast_offers(self):
        """
        Periodically send an offer packet to (BROADCAST_IP, DEFAULT_UDP_PORT),
        advertising self.server_udp_port and self.server_tcp_port for data connections.
        """
        while self.running:
            try:
                # Construct the offer packet as required
                offer_packet = struct.pack(
                    OFFER_STRUCT_FORMAT,
                    MAGIC_COOKIE,
                    MSG_TYPE_OFFER,
                    self.server_udp_port,
                    self.server_tcp_port
                )
                # Broadcast to the known address and port
                self.udp_broadcast_socket.sendto(offer_packet, (BROADCAST_IP, DEFAULT_UDP_PORT))
            except Exception as e:
                print(f"{RED}Broadcast error: {e}{RESET}")

            time.sleep(BROADCAST_INTERVAL)

    def listen_tcp(self):
        """
        Accept incoming TCP connections (with a timeout).
        For each client, spawn a new thread to handle the request.
        """
        while self.running:
            try:
                client_sock, client_addr = self.tcp_server_socket.accept()
                print(f"{YELLOW}New TCP client from {client_addr}{RESET}")
                # Handle each client in its own thread
                threading.Thread(target=self.handle_tcp_client, args=(client_sock,), daemon=True).start()
            except socket.timeout:
                # If no connection arrives within the timeout, loop again
                pass
            except Exception as e:
                print(f"{RED}TCP accept error: {e}{RESET}")

    def handle_tcp_client(self, client_sock):
        """
        1) Read the requested file size.
        2) Send that many bytes of dummy data.
        """
        try:
            data = b""
            # Read byte-by-byte until we find a newline
            while not data.endswith(b"\n"):
                chunk = client_sock.recv(1)
                if not chunk:
                    # Client closed connection
                    return
                data += chunk

            # Convert file size from ASCII to int
            size_str = data.strip().decode()
            try:
                file_size = int(size_str)
            except ValueError:
                print(f"{RED}Invalid file size: {size_str}{RESET}")
                return

            print(f"TCP: client requested {file_size} bytes.")
            # Send the dummy data
            self.send_tcp_data(client_sock, file_size)
        except Exception as e:
            print(f"{RED}TCP client error: {e}{RESET}")
        finally:
            client_sock.close()

    def send_tcp_data(self, sock, size):
        """
        Send 'size' bytes of 'X' in chunks over TCP.
        """
        bytes_sent = 0
        # Defined chunk size to avoid sending the entire file in one go
        chunk_size = 4096
        while bytes_sent < size:
            # Determine how many bytes to send in this iteration
            to_send = min(chunk_size, size - bytes_sent)
            try:
                sock.sendall(b"X" * to_send)
            except Exception as e:
                # If there's a network error, log it and break out of the loop
                print(f"{RED}Error sending TCP data: {e}{RESET}")
                break
            # Update the total number of bytes sent so far
            bytes_sent += to_send

    def listen_udp_requests(self):
        """
        Listen for UDP request packets.
        For each request, spawn a new thread to handle the data transfer.
        """
        while self.running:
            try:
                data, addr = self.udp_request_socket.recvfrom(1024)
                # Check if this packet is large enough for our REQUEST_STRUCT_FORMAT
                if len(data) >= struct.calcsize(REQUEST_STRUCT_FORMAT):
                    magic_cookie_val, msg_type_val, file_size = struct.unpack(REQUEST_STRUCT_FORMAT, data)
                    # Validate the magic cookie and msg_type
                    if magic_cookie_val == MAGIC_COOKIE and msg_type_val == MSG_TYPE_REQUEST:
                        print(f"{YELLOW}UDP: request from {addr}, file_size={file_size}{RESET}")
                        threading.Thread(
                            target=self.handle_udp_transfer,
                            args=(addr, file_size),
                            daemon=True
                        ).start()
            except socket.timeout:
                # No data received, loop again
                pass
            except Exception as e:
                print(f"{RED}UDP request error: {e}{RESET}")

    def handle_udp_transfer(self, client_addr, file_size):
        """
        Send 'file_size' bytes of dummy data over multiple segments.
        The total number of segments is computed based on UDP_PAYLOAD_SIZE.
        """
        total_segments = (file_size // UDP_PAYLOAD_SIZE) + (1 if file_size % UDP_PAYLOAD_SIZE else 0)
        for i in range(total_segments):
            current_seg = i + 1
            # Build the payload header
            header = struct.pack(
                PAYLOAD_STRUCT_FORMAT,
                MAGIC_COOKIE,
                MSG_TYPE_PAYLOAD,
                total_segments,
                current_seg
            )
            # Figure out how many bytes go in this segment
            data_this_segment = min(UDP_PAYLOAD_SIZE, file_size - (i * UDP_PAYLOAD_SIZE))
            dummy_data = b"Y" * data_this_segment

            try:
                # Send header + dummy data to the client
                self.udp_request_socket.sendto(header + dummy_data, client_addr)
            except Exception as e:
                print(f"{RED}UDP send error: {e}{RESET}")
                break

        print(f"{BLUE}UDP: Transfer to {client_addr} completed{RESET}")
