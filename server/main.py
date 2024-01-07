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
       
    
class ControlPlane:
    def __init__(self):
        self._nodes: set[Node] = set()
        self._node_heartbeats = {}

    @property
    def nodes(self):
        return self._nodes

    def register_heartbeat(self, socket: str):
        self._node_heartbeats[socket] = int(time.time())
    
    @nodes.setter
    def register_node_state(self, nodes: set[Node]):
        self._nodes = nodes
        
    def register_node(self, node: Node):
        self._nodes.add(node)

    def remove_node(self, node: Node):
        self._nodes.remove(node)

    def get_node_from_socket(self, socket: str) -> Node | None:
        ip, port = socket.split(':')
        for node in cp.nodes:
            if node.ip == ip and node.port == int(port):
                return node
            else:
                continue

    def get_leader(self) -> Node | None:
        for node in cp.nodes:
            if node.leader is True:
                return node
            else:
                continue

    def get_nodes_sorted(self) -> list[Node]:
        return sorted(list(self._node_heartbeats))


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
cp = ControlPlane()

def broadcast_target(callback):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(('', BROADCAST_PORT))

    try:
        while True:
            data, (ip, port) = listen_socket.recvfrom(1024)
            if data:
                msg = Message.unmarshal(data)
                callback(msg, ip, port)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

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

def heartbeat_target(callback, delay: int):
    try:
        while True:
            new_hb_dict = cp._node_heartbeats.copy()
            for socket, hb in cp._node_heartbeats.items():
                if hb + 2 < int(time.time()):
                    node = cp.get_node_from_socket(socket)
                    cp.remove_node(node)
                    new_hb_dict.pop(socket)
                    if node.leader is True:
                        Message(opcode=OpCode.ELECTION).broadcast()
            cp._node_heartbeats = new_hb_dict
            Message(opcode=OpCode.HEARTBEAT).broadcast()
            time.sleep(delay)
            
    except KeyboardInterrupt:
        exit(0)

def client_hello_handler(message: Message, ip: str, port: int, leader: bool | None = False, server: bool | None = False):
    print(f"Received HELLO from {ip}:{port}")
    print(f"Received HELLO from {ip}:{message.port}")
    cp.register_node(Node(ip, message.port))
    print(f"Sent HELLO_REPLY to {ip}:{message.port}")
    Message(opcode=OpCode.HELLO_REPLY, data=list(map(lambda node: node.__dict__, cp.nodes))).send(ip, message.port)

def hello_handler(message: Message, ip: str, port: int, leader: bool | None = False, server: bool | None = False):
    print(f"Received HELLO from {ip}:{port}")
    print(f"Received HELLO from {ip}:{message.port}")
    cp.register_node(Node(ip, port, leader, True))
    print(f"Sent HELLO_REPLY to {ip}:{message.port}")
    Message(opcode=OpCode.HELLO_REPLY, data=list(map(lambda node: node.__dict__, cp.nodes))).send(ip, message.port)

def transport_handler(message: Message, ip: str, port: int, leader: bool | None = False, server: bool | None = False):
    print(f"Receive data {message.data} from {ip}:{port}")
    print(f"Receive data {message.data} from {ip}:{message.port}")
    print(message)
    Message(opcode=OpCode.TRANSPORT, data="this is the data").send(ip, 8888)

def hello_reply_handler(message: Message, ip: str, port: int):
    print("Received node state")
    print(message)

def heartbeat_handler(message: Message, ip: str, port: int):
    #print(f"Received heartbeat from {ip}:{port}")
    cp.register_heartbeat(f"{ip}:{port}")
    #print(cp._node_heartbeats)

def election_handler(message: Message, ip: str, port: int):
    print(f"Received election from {ip}:{port}")
        
def message_handler(message: Message, ip: str, port: int):
    #print(f"Broadcast message received: {message} from {ip}:{port}", flush=True)
    if message.opcode is OpCode.HELLO_SERVER:
        hello_handler(message, ip, port)
    elif message.opcode is OpCode.HELLO_CLIENT:
        client_hello_handler(message, ip, port)
    elif message.opcode is OpCode.HELLO_REPLY:
        hello_reply_handler(message, ip, port)
    elif message.opcode is OpCode.HEARTBEAT:
        heartbeat_handler(message, ip, port)
    elif message.opcode is OpCode.ELECTION:
        election_handler(message, ip, port)
    elif message.opcode is OpCode.TRANSPORT:
        transport_handler(message, ip, port)
    else:
        return
    print(cp.nodes)
       
def main():
    parser = argparse.ArgumentParser(
        prog='Server'
    )

    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--delay", default=1, type=int)


    args = parser.parse_args()
    print(INTERFACE.ip.compressed)
    print(BROADCAST_IP)
   
    threads = []
    
    listener_thread = Thread(target=broadcast_target, args=(message_handler,))
    listener_thread.start()
    threads.append(listener_thread)

    uni_thread = Thread(target=unicast_target, args=(message_handler, args.port))
    uni_thread.start()
    threads.append(uni_thread)

    heartbeat_thread = Thread(target=heartbeat_target, args=(message_handler, args.delay))
    heartbeat_thread.start()
    threads.append(heartbeat_thread)
    
    Message(OpCode.HELLO_SERVER, port=args.port).broadcast(2)

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
