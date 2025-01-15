# Network Speed Test Assignment

This repository contains a Python assignment that demonstrates a concurrent client-server network speed test over TCP and UDP connections. The code uses multithreading to allow multiple parallel connections and measurement of transfer performance.

---

## Description

- Each server periodically broadcasts an offer packet so clients can receive it. Once an offer packet is received, the server accepts TCP connections and UDP requests on the ports it advertises and sends back a requested amount of data.
- Each client asks the user for file size (in bytes), plus the number of TCP and UDP connections to make. It then listens for a broadcast offer from any server on the local network, connects to the ports advertised and measures throughput, total time, and success rate of packets (for UDP connections).

---

## Features

1. **Threaded Server**:  
   - The server uses separate threads for broadcasting offers, accepting TCP connections and listening for UDP requests. Each incoming request spawns a new thread.

2. **Threaded Client**:  
   - The client spawns a thread per connection (TCP or UDP).

3. **Parallel Downloads**:  
   - Multiple TCP and UDP connections run concurrently, each receiving the full requested file size.

---

## Usage

### Before You Run

1. Ensure you have Python 3 version installed.
2. Optionally, edit the broadcast port and broadcast IP in `Constants.py`:
   - `BROADCAST_IP` (default: `255.255.255.255`)
   - `DEFAULT_UDP_PORT` (default: `13117`)

### Running Instructions

1. Clone or Download this repository.
2. In your terminal, navigate to the folder containing main.py.

#### Running the Server

Execute:

python main.py server

#### Running the Client

Execute:

python main.py client

---

## Project Files

1. **main.py**:

     Entry point deciding whether to run in server or client mode based on the first command-line argument.

2. **NetworkSpeedTest_Server.py**:

     Implements the server logic:
     Broadcasts offers on the chosen port
     Accepts TCP/UDP connections
     Sends dummy data

3. **NetworkSpeedTest_Client.py**:
   
     Implements the client logic:
     Prompts for file size, number of TCP connections, number of UDP connections
     Listens for server offer
     Spawns multiple threads to download concurrently
     Prints out speed and performance stats

4. **Constants.py**:
   
     Defines constants and packet formats
