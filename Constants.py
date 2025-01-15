"""
Constants.py

Holds shared constants for the Network Speed Test application.
"""

import struct
import socket
import threading
import time
import sys

# ANSI Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED   = "\033[91m"
BLUE  = "\033[94m"
RESET = "\033[0m"

# Used to identify our custom packets (offers, requests, payloads).
MAGIC_COOKIE      = 0xabcddcba  
MSG_TYPE_OFFER    = 0x2         
MSG_TYPE_REQUEST  = 0x3         
MSG_TYPE_PAYLOAD  = 0x4         

# BROADCAST_IP is the address to which the server sends broadcast "offer" packets.
# DEFAULT_UDP_PORT is the port on which the client listens for these broadcast offers.
BROADCAST_IP       = "255.255.255.255"
DEFAULT_UDP_PORT   = 13117

# BROADCAST_INTERVAL: frequency at which the server broadcasts offers.
# UDP_TRANSFER_TIMEOUT: if no UDP data arrives for this many seconds, we consider the transfer complete.
# TCP_RECEIVE_BUFFER_SIZE: how many bytes to read at a time in a TCP recv().
# UDP_PAYLOAD_SIZE: size of each UDP data chunk the server sends to the client.
BROADCAST_INTERVAL    = 1.0  
UDP_TRANSFER_TIMEOUT  = 1.0
TCP_RECEIVE_BUFFER_SIZE = 4096
UDP_PAYLOAD_SIZE      = 1024

# Offer:   L for 4-byte cookie, B for 1-byte msg_type, H for 2-byte UDP port, H for 2-byte TCP port
OFFER_STRUCT_FORMAT   = "!LBHH"
# Request: L for 4-byte cookie, B for 1-byte msg_type, Q for 8-byte file size
REQUEST_STRUCT_FORMAT = "!LBQ"
# Payload: L for 4-byte cookie, B for 1-byte msg_type, Q for 8-byte total segments, Q for 8-byte current segment
PAYLOAD_STRUCT_FORMAT = "!LBQQ"
