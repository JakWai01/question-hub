from network import Message, OpCode
import socket
from network import INTERFACE, BROADCAST_PORT
import logging
from control_plane import ControlPlane
import time
from node import Node
from election import Election
import json
from election import ElectionData

def heartbeat_handler(message: Message, ip: str, cp: ControlPlane, election: Election):
    cp.register_heartbeat(f"{ip}:{message.port}")


def election_result_handler(message: Message, ip: str, cp: ControlPlane, election: Election):
    node = cp.get_node_from_socket(f"{ip}:{message.port}")
    cp.make_leader(node)

def broadcast_target(callback, cp: ControlPlane, election: Election):
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

                callback(msg, ip, cp, election)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

def unicast_target(callback, lport: int, cp: ControlPlane, election: Election):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.bind((INTERFACE.ip.compressed, lport))

    try:
        while True:
            data, (ip, port) = listen_socket.recvfrom(1024)
            if data:
                msg = Message.unmarshal(data)
                logging.debug(f"Unicast message received: {msg.opcode}")
                callback(msg, ip, cp, election)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

def heartbeat_target(callback, delay: int, cp: ControlPlane, election: Election):
    try:
        while True:
            new_hb_dict = cp._node_heartbeats.copy()
            for socket, hb in cp._node_heartbeats.items():
                if hb + 2 < int(time.time()):
                    node = cp.get_node_from_socket(socket)
                    cp.remove_node(node)
                    logging.info(f"Lost connection to node: {node.ip}:{node.port}")
                    new_hb_dict.pop(socket)
                    cp._node_heartbeats = new_hb_dict
                    if node.leader is True and len(cp._node_heartbeats) > 1:
                        e = Election(cp)
                        e.initiate_election()

            Message(opcode=OpCode.HEARTBEAT, port=cp.node.port).broadcast()
            cp.register_heartbeat(f"{cp.node.ip}:{cp.node.port}")

            time.sleep(delay)

            if len(cp._node_heartbeats) == 1 and cp.node.leader == False:
                logging.info("Taking leadership since I am the only node left")
                cp.make_leader(cp.node)

    except KeyboardInterrupt:
        exit(0)

def message_handler(message: Message, ip: str, cp: ControlPlane, election: Election):
        if ip == cp.node.ip and message.port == cp.node.port:
            return

        if message.opcode is not OpCode.HEARTBEAT:
            logging.info(
                f"Received message of type {message.opcode.value} from {ip}:{message.port}"
            )

        if message.opcode is OpCode.HELLO:
            hello_handler(message, ip, cp, election)
        elif message.opcode is OpCode.HELLO_REPLY:
            hello_reply_handler(message, ip, cp, election)
        elif message.opcode is OpCode.HEARTBEAT:
            heartbeat_handler(message, ip, cp, election)
        elif message.opcode is OpCode.ELECTION_VOTE or message.opcode is OpCode.ELECTION_REPLY:
            election_handler(message, ip, cp, election)
        elif message.opcode is OpCode.ELECTION_RESULT:
            election_result_handler(message, ip, cp, election)
        else:
            return

def election_handler(message: Message, ip: str, cp: ControlPlane, election: Election):
    sender_socket = f"{ip}:{message.port}"

    next_neighbour = cp.get_next_neighbour(cp.get_node_from_socket(sender_socket))
    previous_neighbour = cp.get_previous_neighbour(cp.get_node_from_socket(sender_socket))
  
    msg = json.loads(message.data)
    
    vote = ElectionData(leader_ip=msg["leader_ip"], leader_port=msg["leader_port"], leader_stat=msg["leader_stat"], hop=msg["hop"], phase=msg["phase"])

    print(vote.__dict__)

    # Handle reply
    if vote.hop is None:
        if vote.leader_stat != cp.node.port:
            vote.hop = None
            Message(opcode=OpCode.ELECTION_REPLY, port=cp.node.port, data=json.dumps(vote.__dict__)).send(next_neighbour.ip, next_neighbour.port)
        else:
            if election.received.get(vote.leader_port) is None:
                election.received[vote.leader_port] = []
            received = election.received.get(vote.leader_port, [])
            # TODO: Use socket instead
            if vote.leader_port in received:
                print("SENDING OUT NEXT PHASE")
                election.send_vote_to_neighbours(phase=vote.phase + 1, hop=1)
            else:
                received.append(vote.leader_port)

    # Handle vote
    else:
        if vote.leader_stat > cp.node.port:
            if vote.hop < 2**vote.phase:
                msg = ElectionData(vote.leader_ip, vote.leader_port, vote.leader_stat, vote.hop + 1, vote.phase)
                Message(opcode=OpCode.ELECTION_VOTE, port=cp.node.port, data=json.dumps(msg.__dict__)).send(next_neighbour.ip, next_neighbour.port)
            elif 2**vote.phase > len(cp.nodes):
                logging.info(f"Invalid election state {vote}")
            else:
                vote.hop = None
                Message(opcode=OpCode.ELECTION_REPLY, port=cp.node.port, data=json.dumps(vote.__dict__)).send(previous_neighbour.ip, previous_neighbour.port)
        elif vote.leader_stat == cp.node.port:
            final = 2**(vote.phase + 1) > len(cp.nodes)
            if final:
                election.received = {}
                cp.make_leader(cp.get_node_from_socket(f"{vote.leader_ip}:{vote.leader_port}"))
                Message(opcode=OpCode.ELECTION_RESULT, port=vote.leader_port).broadcast()

def hello_reply_handler(message: Message, ip: str, cp: ControlPlane, election: Election):
    logging.debug(f"Received node state: {message.data}")

    new_nodes = [
        Node(node["ip"], node["port"], node["leader"]) for node in message.data
    ]

    for node in new_nodes:
        cp.register_heartbeat(f"{node.ip}:{node.port}")

    cp.nodes.update(set(new_nodes))
        
    e = Election(cp)
    e.initiate_election()

def hello_handler(message: Message, ip: str, cp: ControlPlane, election: Election):
    cp.register_node(Node(ip, message.port))

    if cp.current_leader == None or cp.node.leader == True:
        Message(
            opcode=OpCode.HELLO_REPLY,
            port=cp.node.port,
            data=list(map(lambda node: node.__dict__, cp.nodes)),
        ).send(ip, message.port)

