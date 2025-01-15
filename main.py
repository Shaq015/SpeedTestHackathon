"""
main.py

Entry point for running the SpeedTest application.
Usage:
  python main.py server
  python main.py client
"""

import sys
from NetworkSpeedTest_Server import SpeedTestServer
from NetworkSpeedTest_Client import SpeedTestClient

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py server  OR  python main.py client")
        return

    role = sys.argv[1].lower()
    if role == "server":
        # Instantiate and start the server
        server = SpeedTestServer()
        server.start()
    elif role == "client":
        # Instantiate and run the client
        client = SpeedTestClient()
        client.run()
    else:
        print("Unknown argument. Please use 'server' or 'client'.")

if __name__ == "__main__":
    main()
