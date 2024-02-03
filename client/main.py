import sys
import node
import network
import api

import argparse
import socket
import json
from ipaddress import IPv4Interface
import netifaces
import time
from enum import Enum, unique
from threading import Thread
from dataclasses import dataclass

sock = network.sock

# hostname and network interface
HOSTNAME = network.HOSTNAME
INTERFACE = network.INTERFACE

BROADCAST_PORT = network.BROADCAST_PORT
BROADCAST_IP = network.BROADCAST_IP

# def unicast_target(callback, lport: int):
#     listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     listen_socket.bind((INTERFACE.ip.compressed, lport))
#
#     try: 
#         while True:
#             data, (ip, port) = listen_socket.recvfrom(1024)
#             if data:
#                 msg = network.Message.unmarshal(data)
#                 callback(msg, ip, port)
#     except KeyboardInterrupt:
#         listen_socket.close()
#         exit(0)

def data_request(ip: str, port: int):
    print("getting nodes...")
    print("Sent data request to ip:port")
    network.Message(opcode=network.OpCode.TRANSPORT, data="give data plx").send(ip, 8765)

def hello_reply_handler(message: network.Message, ip: str, port: int):
    print(f"Received HELLO_REPLY from {ip}:{port}")
    print(f"Received HELLO_REPLY from {ip}:{message.port}")
    for node in message.data:
        print(node["ip"],":",node["port"])
    #data_request(ip, 8765)
    #print(f"Sent TRANSPORT to {ip}:8765")
    #Message(opcode=OpCode.TRANSPORT, port=message.port, data="give data plx").send(ip, 8765)

def data_receive_handler(message: network.Message, ip: str, port: int):
    print(message.data)
    print(f"Receive data {message.data} from {ip}:{port}")
    print(f"Receive data {message.data} from {ip}:{message.port}")
    print(message)
        

       
def main():
    parser = argparse.ArgumentParser(
        prog='Client'
    )

    parser.add_argument("--port", default=8888, type=int)
    parser.add_argument("--delay", default=10, type=int)

    args = parser.parse_args()
    print(INTERFACE.ip.compressed)
    print(BROADCAST_IP)
   
    threads = []

    uni_thread = Thread(target=api.unicast_target, args=(api.message_handler, args.port))
    uni_thread.start()
    print("uni_thread with", args.port, "started")
    threads.append(uni_thread)
    
    network.Message(network.OpCode.HELLO, port=args.port).broadcast(2)
    print("broadcast sent")

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
