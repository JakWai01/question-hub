import argparse
import socket
import json
from ipaddress import IPv4Interface
import netifaces
import time
from enum import Enum, unique
from threading import Thread
from dataclasses import dataclass

@dataclass
class Node:
    ip: str
    port: int
    leader: bool
    server: bool

    def __init__(cls, ip: str, port: int, leader: bool | None = False, server: bool | None = False):
        cls.ip = ip
        cls.port = port
        cls.leader = leader
        cls.server = server
        
    def __hash__(cls):
        return hash(f"{cls.ip}:{cls.port}") 

class OpCode(str, Enum):
    HELLO_SERVER = "hello_server"
    HELLO_CLIENT = "hello_client"
    HELLO_REPLY = "hello_reply"
    HEARTBEAT = "heartbeat"
    ELECTION = "election"
    TRANSPORT = "transport"
    
class Message():
    def __init__(self, opcode: OpCode, data: bytes | None = None, port: int | None = None):
        self.opcode: OpCode = opcode
        self.data: bytes = data
        self.port: int = port

    def marshal(self):
        return bytes(json.dumps(self.__dict__), "UTF-8")

    @staticmethod
    def unmarshal(data_b: bytes) -> "Message":
        data_str = data_b.decode("UTF-8")
        payload = json.loads(data_str)
        print(payload)
        return Message(OpCode(payload.get("opcode")), payload.get("data"), payload.get("port"))

    def broadcast(self, timeout=0) -> tuple["Message", str, str]:
        return send(self.marshal(), timeout=timeout)

    def send(self, ip: str, port: int, timeout=0) -> tuple["Message", str, str]:
        return send(self.marshal(), (ip, port), timeout=timeout)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send(payload: bytes, address: tuple[str, int] | None = None, timeout=0):
    if address is None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        address = (BROADCAST_IP, BROADCAST_PORT)

    sock.sendto(payload, address)

def is_valid(address: str, broadcast: str | None):
    if not broadcast:
        return False
    if "." not in address:
        return False
    if address == "127.0.0.1":
        return False
    return True

def get_network_interface() -> IPv4Interface:
    for interface in reversed(netifaces.interfaces()):
        for addr, *_ in netifaces.ifaddresses(interface).values():
            address = addr.get("addr", "")
            broadcast = addr.get("broadcast")
            if is_valid(address, broadcast):
                netmask = addr.get("netmask")
                return IPv4Interface(f"{address}/{netmask}")
    raise Exception("Cannot find network interface to listen on")

# hostname and network interface
HOSTNAME = socket.gethostname()
INTERFACE = get_network_interface()

BROADCAST_PORT = 34567
BROADCAST_IP = str(INTERFACE.network.broadcast_address)

def unicast_target(callback, lport: int):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.bind((INTERFACE.ip.compressed, lport))

    try: 
        while True:
            data, (ip, port) = listen_socket.recvfrom(1024)
            if data:
                msg = Message.unmarshal(data)
                callback(msg, ip, port)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

def data_request(ip: str, port: int):
    print("getting nodes...")
    print("Sent data request to ip:port")
    Message(opcode=OpCode.TRANSPORT, data="give data plx").send(ip, 8765)

def hello_reply_handler(message: Message, ip: str, port: int):
    print(f"Received HELLO_REPLY from {ip}:{port}")
    print(f"Received HELLO_REPLY from {ip}:{message.port}")
    for node in message.data:
        print(node["ip"],":",node["port"])
    data_request(ip, 8765)
    #print(f"Sent TRANSPORT to {ip}:8765")
    #Message(opcode=OpCode.TRANSPORT, port=message.port, data="give data plx").send(ip, 8765)

def data_receive_handler(message: Message, ip: str, port: int):
    print(message.data)
    print(f"Receive data {message.data} from {ip}:{port}")
    print(f"Receive data {message.data} from {ip}:{message.port}")
    print(message)
        

def message_handler(message: Message, ip: str, port: int):
    print(f"Broadcast message received: {message} from {ip}:{port}", flush=True)
    if message.opcode is OpCode.HELLO_REPLY:
        hello_reply_handler(message, ip, port)
    elif message.opcode is OpCode.TRANSPORT:
        data_receive_handler(message, ip, port)
    else:
        return
       
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

    uni_thread = Thread(target=unicast_target, args=(message_handler, args.port))
    uni_thread.start()
    threads.append(uni_thread)
    
    Message(OpCode.HELLO_CLIENT, port=args.port).broadcast(2)

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
