"""
NetworkSpeedTest_Client.py

Implements the SpeedTestClient class, which:
1) Asks the user for the file size, number of TCP connections and number of UDP connections upon initialization.
2) Listens for a server's broadcast on DEFAULT_UDP_PORT.
3) Once an offer is received, runs the speed test.
4) Measures transfer speed and prints statistics.
"""

from Constants import *
import socket
import struct
import threading
import time
import sys

class SpeedTestClient:
    def __init__(self):
        """Initialize the client, gather user input, then bind a UDP socket to listen for offers."""
        # Prompt user for input parameters (file_size, tcp_count, udp_count)
        self.file_size, self.tcp_count, self.udp_count = self.get_user_input()

        # Create the UDP socket for receiving broadcasts from the server and enable broadcast reading
        self.client_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.client_udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.client_udp_socket.settimeout(0.5) 

        # Bind to 0.0.0.0:DEFAULT_UDP_PORT so we can receive broadcast on DEFAULT_UDP_PORT 
        self.client_udp_socket.bind(("0.0.0.0", DEFAULT_UDP_PORT))

        self.running = True
        print(f"{GREEN}Client started, listening for offer requests...{RESET}")

    def run(self):
        """
        In a loop:
        1) Listen for a server offer, with a 10-second timeout.
        2) If an offer is received, start the speed test.
        3) After finishing the test, go back to listening for new offers.
        """
        while self.running:
            print(f"{BLUE}\nLooking for a server offer... (Ctrl+C to quit){RESET}")
            offer = self.listen_for_offer()
            if not offer:
                # If no offer was received within the timeout, loop again
                continue

            server_ip, srv_udp_port, srv_tcp_port = offer
            print(f"{GREEN}Received offer from {server_ip}{RESET}")
            print(f"Initiating speed test => UDP:{srv_udp_port}, TCP:{srv_tcp_port}")

            # Start the speed test with the specified file size and connection counts
            self.start_speed_test(server_ip, srv_udp_port, srv_tcp_port, 
                                  self.file_size, self.tcp_count, self.udp_count)

            print(f"{GREEN}All transfers complete, listening to offer requests...{RESET}")

    def get_user_input(self):
        """
        Prompt the user for file size, number of TCP connections and number of UDP connections.
        Return the specified parameters.
        """
        while True:
            try:
                fsize = int(input("Enter file size (in bytes): "))
                tcp_c = int(input("Enter number of TCP connections: "))
                udp_c = int(input("Enter number of UDP connections: "))
                # Checks to ensure valid input
                if fsize <= 0 or tcp_c < 0 or udp_c < 0:
                    raise ValueError
                return fsize, tcp_c, udp_c
            except ValueError:
                print(f"{RED}Invalid input, please try again.{RESET}")

    def listen_for_offer(self):
        """
        Wait up to 10 seconds for a broadcast offer packet on DEFAULT_UDP_PORT.
        Return (server_ip, server_udp_port, server_tcp_port) on success, or None if timed out.
        """
        start_time = time.time()
        while True:
            if (time.time() - start_time) > 10:
                # Timed out after 10s
                print(f"{RED}No server offer received within 10 seconds. Retrying...{RESET}")
                return None
            try:
                data, addr = self.client_udp_socket.recvfrom(1024)
                if len(data) >= struct.calcsize(OFFER_STRUCT_FORMAT):
                    # Unpack the offer packet
                    mc_val, msg_val, srv_udp_port, srv_tcp_port = struct.unpack(OFFER_STRUCT_FORMAT, data)
                    if mc_val == MAGIC_COOKIE and msg_val == MSG_TYPE_OFFER:
                        # Valid offer
                        return (addr[0], srv_udp_port, srv_tcp_port)
            except socket.timeout:
                # No data received, keep looping
                pass
            except KeyboardInterrupt:
                print(f"{RED}Client shutting down by user request...{RESET}")
                sys.exit(0)
            except Exception as e:
                print(f"{RED}Error receiving offer: {e}{RESET}")
                return None

    def start_speed_test(self, server_ip, srv_udp_port, srv_tcp_port, file_size, tcp_count, udp_count):
        """
        Launch threads for each TCP and UDP download, wait for all to finish, print stats.
        """
        threads = []

        # Start TCP connections
        for i in range(tcp_count):
            t = threading.Thread(
                target=self.handle_tcp_transfer,
                args=(server_ip, srv_tcp_port, file_size, i+1)
            )
            t.start()
            threads.append(t)

        # Start UDP connections
        for i in range(udp_count):
            t = threading.Thread(
                target=self.handle_udp_transfer,
                args=(server_ip, srv_udp_port, file_size, i+1)
            )
            t.start()
            threads.append(t)

        # Wait for all threads to complete before returning
        for t in threads:
            t.join()

    def handle_tcp_transfer(self, server_ip, server_tcp_port, file_size, idx):
        """
        Single TCP transfer thread:
          1) Connect to the server on (server_ip, server_tcp_port).
          2) Send the file_size.
          3) Receive 'file_size' bytes of dummy data, or stop if the server closes.
          4) Print timing and throughput stats.
        """
        start_time = time.time()
        received = 0
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5) 
                s.connect((server_ip, server_tcp_port))
                # Send the requested file_size
                s.sendall(str(file_size).encode() + b"\n")

                # Keep reading until we've received the entire size or until the server closes
                while received < file_size:
                    chunk = s.recv(TCP_RECEIVE_BUFFER_SIZE)
                    if not chunk:
                        break
                    received += len(chunk)
        except Exception as e:
            print(f"{RED}TCP error (#{idx}): {e}{RESET}")

        end_time = time.time()
        duration = max(end_time - start_time, 1e-6)  # avoid division by zero
        speed_bps = (received * 8) / duration
        print(f"{GREEN}TCP transfer #{idx} finished, total time: {duration:.3f} seconds, total speed: {speed_bps:.2f} bits/seconds{RESET}")

    def handle_udp_transfer(self, server_ip, server_udp_port, file_size, idx):
        """
        Single UDP transfer thread:
          1) Sends a request packet (MSG_TYPE_REQUEST, file_size) from an ephemeral local port.
          2) Continuously receives data until no packets arrive for UDP_TRANSFER_TIMEOUT.
          3) Calculates total bytes, throughput and success rate.
        """
        start_time = time.time()
        total_bytes = 0
        total_segments = 0
        segments_received = 0

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_sock:
            # Bind ephemeral local port for receiving server's payload
            udp_sock.bind(("0.0.0.0", 0))
            udp_sock.settimeout(UDP_TRANSFER_TIMEOUT)

            # Build request
            request_packet = struct.pack(
                REQUEST_STRUCT_FORMAT,
                MAGIC_COOKIE,
                MSG_TYPE_REQUEST,
                file_size
            )
            # Send request to the server's ephemeral UDP port
            udp_sock.sendto(request_packet, (server_ip, server_udp_port))
            last_data_time = time.time()

            # Keep receiving until we time out waiting for data
            while True:
                try:
                    data, _ = udp_sock.recvfrom(1500)
                    if len(data) < struct.calcsize(PAYLOAD_STRUCT_FORMAT):
                        # Short or invalid packet
                        continue

                    # Parse the header from the payload
                    mc, mt, total_seg, current_seg = struct.unpack(
                        PAYLOAD_STRUCT_FORMAT,
                        data[:struct.calcsize(PAYLOAD_STRUCT_FORMAT)]
                    )
                    if mc != MAGIC_COOKIE or mt != MSG_TYPE_PAYLOAD:
                        # Different payload
                        continue

                    total_segments = total_seg
                    segments_received += 1
                    # The rest of the data is the dummy payload
                    payload_data = data[struct.calcsize(PAYLOAD_STRUCT_FORMAT):]
                    total_bytes += len(payload_data)
                    last_data_time = time.time()
                except socket.timeout:
                    # If last_data_time exceeds UDP_TRANSFER_TIMEOUT, break
                    if time.time() - last_data_time > UDP_TRANSFER_TIMEOUT:
                        break

        end_time = time.time()
        duration = max(end_time - start_time, 1e-6)  # avoid division by zero
        speed_bps = (total_bytes * 8) / duration

        success_rate = 0.0
        if total_segments > 0:
            success_rate = (segments_received / total_segments) * 100

        print(f"{BLUE}UDP transfer #{idx} finished, total time: {duration:.3f} seconds, total speed: {speed_bps:.2f} bits/seconds, percentage of packets received successfully: {success_rate:.2f}%{RESET}")
