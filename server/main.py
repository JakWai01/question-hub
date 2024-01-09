import argparse
import socket
import json
from ipaddress import IPv4Interface
import netifaces
import time
from enum import Enum, unique
from threading import Thread
from dataclasses import dataclass

class OpCode(str, Enum):
    HELLO = "hello"
    HELLO_REPLY = "hello_reply"
    HEARTBEAT = "heartbeat"
    ELECTION = "election"
    
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
        # print(payload)
        return Message(OpCode(payload.get("opcode")), payload.get("data"), payload.get("port"))

    def broadcast(self, timeout=0) -> tuple["Message", str, str]:
        return send(self.marshal(), timeout=timeout)

    def send(self, ip: str, port: int, timeout=0) -> tuple["Message", str, str]:
        return send(self.marshal(), (ip, port), timeout=timeout)

@dataclass
class Node:
    ip: str
    port: int
    leader: bool

    def __init__(cls, ip: str, port: int, leader: bool | None = False):
        cls.ip = ip
        cls.port = port
        cls.leader = leader
        
    def __hash__(cls):
        return hash(f"{cls.ip}:{cls.port}") 
 
    def broadcast_target(cls, callback):
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind(('', BROADCAST_PORT))

        try:
            while True:
                data, (ip, port) = listen_socket.recvfrom(1024)
                if data:
                    msg = Message.unmarshal(data)
                    callback(msg, ip)
        except KeyboardInterrupt:
            listen_socket.close()
            exit(0)

    def unicast_target(cls, callback, lport: int):
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.bind((INTERFACE.ip.compressed, lport))

        try: 
            while True:
                data, (ip, port) = listen_socket.recvfrom(1024)
                if data:
                    msg = Message.unmarshal(data)
                    callback(msg, ip)
        except KeyboardInterrupt:
            listen_socket.close()
            exit(0)

    def heartbeat_target(cls, callback, delay: int):
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
                Message(opcode=OpCode.HEARTBEAT, port=cls.port).broadcast()
                time.sleep(delay)
                
        except KeyboardInterrupt:
            exit(0)      

    def message_handler(cls, message: Message, ip: str):
        print(f"Broadcast message received from {ip}:{message.port}", flush=True)

        # Drop broadcast messages sent by the node itself
        if ip == cls.ip and message.port == cls.port:
            print("Received message by myself")
            return
        elif message.opcode is OpCode.HELLO:
            hello_handler(message, ip)        
        elif message.opcode is OpCode.HELLO_REPLY:
            hello_reply_handler(message, ip)
        elif message.opcode is OpCode.HEARTBEAT:
            heartbeat_handler(message, ip)
        elif message.opcode is OpCode.ELECTION:
            cls.election_handler(message, ip)
        else:
            return
        print(cp.nodes)
    
    # For now, the node with the heighest port wins. Later on, the most up to date
    # data shall be used
    # We can also not solely rely on ports since ports could be the same but the IP could differ
    def election_handler(cls, message: Message, ip: str):
        print(f"Received election from {ip}:{message.port}")
        print(cp.get_nodes_sorted().index(f'{cls.ip}:{cls.port}'))
   
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
        print(f"pre sorted {self._node_heartbeats}")
        print(cp.nodes)
        return sorted(list(self._node_heartbeats))


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

def hello_handler(message: Message, ip: str):
    cp.register_node(Node(ip, message.port))
    Message(opcode=OpCode.HELLO_REPLY, data=list(map(lambda node: node.__dict__, cp.nodes))).send(ip, message.port)

def hello_reply_handler(message: Message, ip: str):
    print("Received node state")
    for node in message.data:
        cp.register_node(Node(node["ip"], node["port"], node["leader"]))
    print(f"Nodes before election {cp.nodes}")
    Message(opcode=OpCode.ELECTION).broadcast()

def heartbeat_handler(message: Message, ip: str):
    print(f"Received heartbeat from {ip}:{message.port}")
    cp.register_heartbeat(f"{ip}:{message.port}")
    print(cp._node_heartbeats)
       
def main():
    parser = argparse.ArgumentParser(
        prog='Server'
    )

    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--delay", default=1, type=int)

    args = parser.parse_args()
    # print(INTERFACE.ip.compressed)
    # print(BROADCAST_IP)
   
    threads = []

    # Initialize oneself. Start by declaring our self as the leader
    node = Node(INTERFACE.ip.compressed, args.port, True)
    cp.register_node(node)

    listener_thread = Thread(target=node.broadcast_target, args=(node.message_handler,))
    listener_thread.start()
    threads.append(listener_thread)

    uni_thread = Thread(target=node.unicast_target, args=(node.message_handler, node.port))
    uni_thread.start()
    threads.append(uni_thread)

    heartbeat_thread = Thread(target=node.heartbeat_target, args=(node.message_handler, args.delay))
    heartbeat_thread.start()
    threads.append(heartbeat_thread)
    
    Message(OpCode.HELLO, port=node.port).broadcast(2)

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
