from network import Message, OpCode
import socket
from network import INTERFACE, BROADCAST_PORT
import logging
from control_plane import ControlPlane
import time
from node import Node
from election import Election

def heartbeat_handler(message: Message, ip: str, cp: ControlPlane):
    cp.register_heartbeat(f"{ip}:{message.port}")


def election_result_handler(message: Message, ip: str, cp: ControlPlane):
    new_leader = cp.get_node_from_socket(f"{ip}:{message.port}")
    new_leader.leader = True

    if cp.current_leader is not None:
        cp.current_leader.leader = False

    cp.current_leader = new_leader
    logging.info(
        f"Node {cp.current_leader.ip}:{cp.current_leader.port} has been appointed the new leader"
    )

def broadcast_target(callback, cp: ControlPlane):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(("", BROADCAST_PORT))

    try:
        while True:
            data, (ip, port) = listen_socket.recvfrom(1024)
            if data:
                msg = Message.unmarshal(data)

                logging.debug(f"Broadcast message received: {msg.opcode}")

                callback(msg, ip, cp)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

def unicast_target(callback, lport: int, cp: ControlPlane):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.bind((INTERFACE.ip.compressed, lport))

    try:
        while True:
            data, (ip, port) = listen_socket.recvfrom(1024)
            if data:
                msg = Message.unmarshal(data)
                logging.debug(f"Unicast message received: {msg.opcode}")
                callback(msg, ip, cp)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

def heartbeat_target(callback, delay: int, cp: ControlPlane):
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
                        cp.initiate_election()

            Message(opcode=OpCode.HEARTBEAT, port=cp.node.port).broadcast()
            cp.register_heartbeat(f"{cp.node.ip}:{cp.node.port}")

            time.sleep(delay)

            if len(cp._node_heartbeats) == 1 and cp.node.leader == False:
                logging.info("Taking leadership since I am the only node left")
                cp.make_leader(cp.node)

    except KeyboardInterrupt:
        exit(0)

def message_handler(message: Message, ip: str, cp: ControlPlane):
        # Drop broadcast messages sent by the node itself
        if ip == cp.node.ip and message.port == cp.node.port:
            return

        if message.opcode is not OpCode.HEARTBEAT:
            logging.info(
                f"Received message of type {message.opcode.value} from {ip}:{message.port}"
            )
        
        # print(message.data)

        if message.opcode is OpCode.HELLO:
            hello_handler(message, ip, cp)
        elif message.opcode is OpCode.HELLO_REPLY:
            hello_reply_handler(message, ip, cp)
        elif message.opcode is OpCode.HEARTBEAT:
            heartbeat_handler(message, ip, cp)
        elif message.opcode is OpCode.ELECTION:
            election_handler(message, ip, cp)
        elif message.opcode is OpCode.ELECTION_RESULT:
            election_result_handler(message, ip, cp)
        else:
            return

def election_handler(message: Message, ip: str, cp: ControlPlane):
    sender_socket = f"{ip}:{message.port}"
    next_neighbour = cp.node.get_next_neighbour(sender_socket)
    previous_neighbour = cp.node.get_previous_neighbour(sender_socket)
    
    msg = json.loads(message.data)
    
    # print((json.loads(msg))["leader_ip"])
    vote = ElectionData(leader_ip=msg["leader_ip"], leader_port=msg["leader_port"], leader_stat=msg["leader_stat"], hop=msg["hop"], phase=msg["phase"])

    # print(vote)

    # Handle reply
    if vote.hop is None:
        if vote.leader_stat != cp.node.port:
            vote.hop = None
            Message(opcode=opcode.ELECTION, port=cp.node.port, data=json.dumps(vote.__dict__)).send(next_neighbour.ip, next_neighbour.port)
        else:
            if  cls.received.get(vote.leader_port) is None:
                cls.received[vote.leader_port] = []
            received = cls.received.get(vote.leader_port, [])
            # TODO: Use socket instead
            if vote.leader_port in received:
                cls.send_vote_to_neighbours(phase=vote.phase + 1, hop=1)
            else:
                received.append(vote.leader_port)
    # Handle vote
    else:
        if vote.leader_stat > cls.port:
            if vote.hop < 2**vote.phase:
                msg = ElectionData(vote.leader_ip, vote.leader_port, vote.leader_stat, vote.hop + 1, vote.phase)
                Message(opcode=OpCode.ELECTION, port=cls.port, data=json.dumps(msg.__dict__)).send(next_neighbour.ip, next_neighbour.port)
            elif 2**vote.phase > len(cp.nodes):
                logging.info(f"Invalid election state {vote}")
            else:
                vote.hop = None
                Message(opcode=OpCode.ELECTION, port=cls.port, data=json.dumps(vote.__dict__)).send(previous_neighbour.ip, previous_neighbour.port)
        elif vote.leader_stat == cls.port:
            final = 2**(vote.phase + 1) > len(cp.nodes)
            if final:
                cp.leader = cp.get_node_from_socket(f"{vote.leader_ip}:{vote.leader_port}")

def hello_reply_handler(message: Message, ip: str, cp: ControlPlane):
    logging.debug(f"Received node state: {message.data}")

    new_nodes = [
        Node(node["ip"], node["port"], node["leader"]) for node in message.data
    ]

    # Register nodes and heartbeats
    for node in new_nodes:
        cp.register_heartbeat(f"{node.ip}:{node.port}")

    cp.nodes.update(set(new_nodes))
    
    e = Election(cp)
    e.initiate_election()

def hello_handler(message: Message, ip: str, cp: ControlPlane):
    cp.register_node(Node(ip, message.port))

    if cp.current_leader == None or cp.node.leader == True:
        Message(
            opcode=OpCode.HELLO_REPLY,
            port=cp.node.port,
            data=list(map(lambda node: node.__dict__, cp.nodes)),
        ).send(ip, message.port)

