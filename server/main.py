import argparse
import socket
import json
from ipaddress import IPv4Interface
import netifaces
import time
from enum import Enum, unique
from threading import Thread
from dataclasses import dataclass
import logging


class OpCode(str, Enum):
    HELLO = "hello"
    HELLO_REPLY = "hello_reply"
    HEARTBEAT = "heartbeat"
    ELECTION = "election"
    ELECTION_VOTE = "election_vote"
    ELECTION_REPLY = "election_reply"
    ELECTION_RESULT = "election_result"

class Election:
    received: dict[str, list[tuple[int, float]]] = {}
    
class ElectionData:
    def __init__(self, leader_ip: str, leader_port: int, leader_stat: int, hop: int | None, phase: int):
        self.leader_ip = leader_ip
        self.leader_port = leader_port
        self.leader_stat = leader_stat
        self.hop = hop
        self.phase = phase

class Message:
    def __init__(
        self, opcode: OpCode, data: bytes | None = None, port: int | None = None
    ):
        self.opcode: OpCode = opcode
        self.data: bytes = data
        self.port: int = port

    def marshal(self):
        return bytes(json.dumps(self.__dict__), "UTF-8")

    @staticmethod
    def unmarshal(data_b: bytes) -> "Message":
        data_str = data_b.decode("UTF-8")
        payload = json.loads(data_str)
        logging.debug(f"Unmarshalled payload {payload}")
        return Message(
            OpCode(payload.get("opcode")), payload.get("data"), payload.get("port")
        )

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

    
    def make_leader(cls):
        if cp.current_leader is not None:
            cp.current_leader.leader = False

        cls.leader = True
        cp.current_leader = cls

    def initiate_election(cls):
        logging.info("Starting a new election")

        if len(cp._node_heartbeats) == 1:
            logging.info("We are the only node")
            cls.make_leader()
            return

        cls.send_vote_to_neighbours(phase=0, hop=1)

    def send_vote_to_neighbours(cls, phase: int | None = 0 , hop: int | None = 1):
        msg = ElectionData(cls.ip, cls.port, cls.port, hop, phase)

        right_neihghbour = cls.right_neighbour
        left_neighbour = cls.left_neighbour

        for node in [left_neighbour, right_neighbour]:
            Message(opcode=ELECTION_VOTE, port=cls.port, data=json.dumps(msg.__dict__)).send(node.ip, node.port)

    def get_next_neighbour(socket: str):
        socket_ring_index = cp.get_nodes_sorted.index(socket)

        if socket_ring_index < cls.ring_index:
            return cls.left_neighbour()
        else:
            return cls.right_neighbour()

    @property
    def ring_index(cls):
        return cp.get_nodes_sorted.index(f"{cls.ip}:{cls.port}")

    @property
    def left_neighbour(self):
        return cp.get_nodes_sorted[(cls.ring_index - 1) % len(nodes)]
    
    @property
    def right_neighbour(self):
        return cp.get_nodes_sorted[(cls.ring_index + 1) % len(nodes)]
        
    def broadcast_target(cls, callback):
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind(("", BROADCAST_PORT))

        try:
            while True:
                data, (ip, port) = listen_socket.recvfrom(1024)
                if data:
                    msg = Message.unmarshal(data)

                    if ip != cls.ip:
                        logging.debug(f"Broadcast message received: {msg.opcode}")

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
                    logging.debug(f"Unicast message received: {msg.opcode}")
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
                        logging.debug(f"Node to be removed due to timeout: {node}")
                        new_hb_dict.pop(socket)
                        cp._node_heartbeats = new_hb_dict
                        if node.leader is True:
                            next_node_index = (
                                cp.get_nodes_sorted().index(f"{cls.ip}:{cls.port}") + 1
                            )
                            if next_node_index >= len(cp.nodes):
                                next_node_index = 0

                            next_node = cp.get_node_from_socket(
                                cp.get_nodes_sorted()[next_node_index]
                            )

                            Message(
                                opcode=OpCode.ELECTION,
                                port=cls.port,
                                data=json.dumps(
                                    ElectionData(cls.ip, cls.port, 0).__dict__
                                ),
                            ).send(next_node.ip, next_node.port)
                Message(opcode=OpCode.HEARTBEAT, port=cls.port).broadcast()
                cp.register_heartbeat(f"{cls.ip}:{cls.port}")

                # If we wait before, we should get other heartbeats before
                time.sleep(delay)

                # If we are the only server node alive after waiting two seconds, we are the leader
                if len(cp._node_heartbeats) == 1 and cls.leader == False:
                    logging.info("Taking leadership since I am the only node left")
                    cls.make_leader()

        except KeyboardInterrupt:
            exit(0)

    def message_handler(cls, message: Message, ip: str):
        # Drop broadcast messages sent by the node itself
        if ip == cls.ip and message.port == cls.port:
            return

        logging.info(
            f"Received message of type {message.opcode.value} from {ip}:{message.port}"
        )

        if message.opcode is OpCode.HELLO:
            cls.hello_handler(message, ip)
        elif message.opcode is OpCode.HELLO_REPLY:
            cls.hello_reply_handler(message, ip)
        elif message.opcode is OpCode.HEARTBEAT:
            heartbeat_handler(message, ip)
        elif message.opcode is OpCode.ELECTION:
            cls.election_handler(message, ip)
        elif message.opcode is OpCode.ELECTION_RESULT:
            election_result_handler(message, ip)
        else:
            return

    # For now, the node with the heighest port wins. Later on, the most up to date
    # data shall be used
    # We can also not solely rely on ports since ports could be the same but the IP could differ
    def election_handler(cls, message: Message, ip: str):
        sender_socket = f"{ip}:{message.data['port']}"
        next_neighbour = cls.get_next_neighbour(sender_socket)
        
        vote = ElectionData(**message.data)

        if vote.hop is 0:
            if vote.port != cls.port:
                logging.info(f"Passing reply {vote} to {next_neighbour}")
                Message(opcode=opcode.ELECTION_REPLY, port=cls.port, data=vote)
            else:
                logging.info(f"Received vote {vote}")
                if self.received.get(vote.socket) is None:
                    self.received[vote.socket] = []
                received = self.received.get(vote.socket, [])
                if vote in received:
                    self.send_vote_to_neighbours(vote.socket, phase=vote.phase + 1, hop=1)
                else:
                    received.append(vote)
        else:
            if vote.port > cls.port:
                if vote.hop < 2**vote.phase:
                    msg = ElectionData(vote.leader_ip, vote_leader_port, vote.leader_stat, vote.hop + 1, vote.phase)
                    logging.info(f"Sending request {msg} to {next_neighbour}")
                    Message(opcode=opcode.ELECTION_VOTE, port=cls.port, data=msg.__dict__).send(next_neighbour.ip, next_neighbour.port)
                elif 2**vote.phase > len(cp.nodes):
                    logging.debug(f"Invalid election state {vote}")
                else:
                    # This will be a bug
                    vote.hop = 0
                    logging.info(f"Sending reply {vote} to {previous_neighbour}")
                    Message(opcode=opcode.ELECTION_REPLY, port=cls.port, data=vote.__dict__)
            elif vote.port == cls.port:
                final = 2**(vote.phase + 1) > len(cp.nodes)
                if final:
                    logging.info(f"Elected {vote.ip}:{vote.port} as leader")
                    cp.leader = cp.get_node_from_socket(f"{vote.ip}:{vote.port}")

                    
                


    def hello_reply_handler(cls, message: Message, ip: str):
        logging.debug(f"Received node state: {message.data}")

        new_nodes = [
            Node(node["ip"], node["port"], node["leader"]) for node in message.data
        ]

        # Register nodes and heartbeats
        for node in new_nodes:
            cp.register_heartbeat(f"{node.ip}:{node.port}")

        cp.nodes.update(set(new_nodes))

        pre_existing_leader = False

        # If no node is the leader so far, start an election. This happens when two nodes start at the same time
        for node in cp.nodes:
            if node.leader == True:
                pre_existing_leader = True
                cp.current_leader = node
            else:
                continue

        if pre_existing_leader == False:
            # Start election to figure out if you should be the new leader
            next_node_index = cp.get_nodes_sorted().index(f"{cls.ip}:{cls.port}") + 1
            if next_node_index >= len(cp.nodes):
                next_node_index = 0

            next_node = cp.get_node_from_socket(cp.get_nodes_sorted()[next_node_index])

            Message(
                opcode=OpCode.ELECTION,
                port=cls.port,
                data=json.dumps(ElectionData(cls.ip, cls.port, 0).__dict__),
            ).send(next_node.ip, next_node.port)

    # TODO: Taking leadership since I am the only node left when in fact two nodes are available
    def hello_handler(cls, message: Message, ip: str):
        cp.register_node(Node(ip, message.port))

        if cp.current_leader == None or cls.leader == True:
            Message(
                opcode=OpCode.HELLO_REPLY,
                port=cls.port,
                data=list(map(lambda node: node.__dict__, cp.nodes)),
            ).send(ip, message.port)


class ControlPlane:
    def __init__(self):
        self._nodes: set[Node] = set()
        self._node_heartbeats = {}
        self.current_leader: Node = None

    @property
    def nodes(self):
        return self._nodes

    def register_heartbeat(self, socket: str):
        self._node_heartbeats[socket] = int(time.time())

    @nodes.setter
    def nodes(self, new_nodes: set[Node]):
        self._nodes = new_nodes

    def register_node(self, node: Node):
        self._nodes.add(node)

    def remove_node(self, node: Node):
        self._nodes.remove(node)

    def get_node_from_socket(self, socket: str) -> Node | None:
        ip, port = socket.split(":")
        for node in cp.nodes:
            if node.ip == ip and node.port == int(port):
                return node
            else:
                continue

    def get_leader(self) -> Node | None:
        return cp.current_leader

    def get_nodes_sorted(self) -> list[Node]:
        return sorted(list(self._node_heartbeats))


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send(payload: bytes, address: tuple[str, int] | None = None, timeout=0):
    if address is None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        address = (BROADCAST_IP, BROADCAST_PORT)

    logging.info(
        f"Sending message of type {json.loads(payload)['opcode']} to {address[0]}:{address[1]}"
    )

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


def heartbeat_handler(message: Message, ip: str):
    cp.register_heartbeat(f"{ip}:{message.port}")


def election_result_handler(message: Message, ip: str):
    new_leader = cp.get_node_from_socket(f"{ip}:{message.port}")
    new_leader.leader = True

    if cp.current_leader is not None:
        cp.current_leader.leader = False

    cp.current_leader = new_leader
    logging.info(
        f"Node {cp.current_leader.ip}:{cp.current_leader.port} has been appointed the new leader"
    )


def main():
    parser = argparse.ArgumentParser(prog="Server")

    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--delay", default=1, type=int)
    parser.add_argument("--loglevel", default="INFO", type=str)

    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    threads = []

    node = Node(INTERFACE.ip.compressed, args.port, False)
    cp.register_node(node)

    listener_thread = Thread(target=node.broadcast_target, args=(node.message_handler,))
    listener_thread.start()
    threads.append(listener_thread)

    uni_thread = Thread(
        target=node.unicast_target, args=(node.message_handler, node.port)
    )
    uni_thread.start()
    threads.append(uni_thread)

    heartbeat_thread = Thread(
        target=node.heartbeat_target, args=(node.message_handler, args.delay)
    )
    heartbeat_thread.start()
    threads.append(heartbeat_thread)

    Message(OpCode.HELLO, port=node.port).broadcast(2)

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
