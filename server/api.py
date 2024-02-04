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
# from application_state import ApplicationState, Question, Vote

# def application_state_handler(message: Message, ip: str, cp: ControlPlane, election: Election, app_state: ApplicationState):
#     msg = json.loads(message.data)
#
#     print(msg)

# Vote for an existing question. If the leader does not know about the question, the question does not exist. 
# Each question is assigned a unique UUID for identification purposes
def vote_request_handler(message: Message, ip: str, cp: ControlPlane, election: Election,
                         # app_state: ApplicationState
                         ):
    msg = json.loads(message.data)
    #question = app_state.get_question_from_uuid(msg.uuid)

    vote = Vote(msg.socket, msg.uuid)

    question.toggle_vote(vote)
    Message(opcode=OpCode.VOTE, port=cp.node.port, data=json.dumps(vote.__dict__)).broadcast()

# Since only the leader handles the request, the other servers also need to receive the update. This happens via the broadcast.
def vote_handler(message: Message, ip: str, cp: ControlPlane, election: Election, 
                 # app_state: ApplicationState
                 ):
    msg = json.loads(message.data)
    #question = app_state.get_question_from_uuid(msg.uuid)

    vote = Vote(msg.socket, msg.uuid)

    question.toggle_vote(vote)

# Post a new question to the application
def question_request_handler(message: Message, ip: str, cp: ControlPlane, election: Election, 
                             #app_state: ApplicationState
                             ):
    msg = json.loads(message.data)
    
    question = Question(msg.text)
    #app_state.add_question(question)

    Message(opcode=OpCode.QUESTION, port=cp.node.port, data=json.dumps(question.__dict__)).broadcast()

def question_handler(message: Message, ip: str, cp: ControlPlane, election: Election, 
                     #app_state: ApplicationState
                     ):
    msg = json.loads(message.data)
    
    question = Question(msg.text)
    #app_state.add_question(question)

def heartbeat_handler(message: Message, ip: str, cp: ControlPlane, election: Election):
    cp.register_heartbeat(f"{ip}:{message.port}")


def election_result_handler(
    message: Message, ip: str, cp: ControlPlane, election: Election
):
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

                    if (
                        node.leader is True
                        and len(cp._node_heartbeats) > 1
                        and str(cp.node.port)
                        == str.split(max(cp._node_heartbeats), ":")[1]
                    ):
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


def message_handler(message: Message, ip: str, cp: ControlPlane, election: Election, 
                    #app_state: ApplicationState
                    ):
    if ip == cp.node.ip and message.port == cp.node.port:
        return

    if message.opcode is not OpCode.HEARTBEAT:
        logging.info(
            f"Received message of type {message.opcode.value} from {ip}:{message.port}"
        )

    if message.opcode is OpCode.HELLO:
        hello_handler(message, ip, cp, election)
    elif message.opcode is OpCode.HELLO_REPLY:
        hello_reply_handler(message, ip, cp, election, 
                            #app_state
                            )
    elif message.opcode is OpCode.HELLO_SERVER:
        hello_handler(message, ip, cp, election)
    elif message.opcode is OpCode.HELLO_CLIENT:
        client_hello_handler(message, ip, cp, election)
    # elif message.opcode is OpCode.TRANSPORT:
    #     transport_handler(message, ip, port)
    elif message.opcode is OpCode.HEARTBEAT:
        heartbeat_handler(message, ip, cp, election)
    elif (
        message.opcode is OpCode.ELECTION_VOTE
        or message.opcode is OpCode.ELECTION_REPLY
    ):
        election_handler(message, ip, cp, election)
    elif message.opcode is OpCode.ELECTION_RESULT:
        election_result_handler(message, ip, cp, election)
    elif message.opcode is OpCode.QUESTION_REQUEST:
        question_request_handler(message, ip, cp, election, 
                                 #app_state
                                 )
    elif message.opcode is OpCode.VOTE_REQUEST:
        vote_request_handler(message, ip, cp, election, 
                             #app_state
                             )
    elif message.opcode is OpCode.VOTE:
        vote_handler(message, ip, cp, election, 
                     #app_state
                     )
    elif message.opcode is OpCode.QUESTION:
        question_handler(message, ip, cp, election, 
                         #app_state
                         )
    # elif message.opcode is OpCode.APPLICATION_STATE:
    #     application_state_handler(message, ip, cp, election, app_state)
    else:
        return


def election_handler(message: Message, ip: str, cp: ControlPlane, election: Election):
    sender_socket = f"{ip}:{message.port}"
    next_neighbour = cp.get_next_neighbour(cp.get_node_from_socket(sender_socket))
    previous_neighbour = cp.get_node_from_socket(f"{ip}:{message.port}")

    msg = json.loads(message.data)

    vote = ElectionData(
        gid=msg["gid"],
        leader_ip=msg["leader_ip"],
        leader_port=msg["leader_port"],
        leader_stat=msg["leader_stat"],
        hop=msg["hop"],
        phase=msg["phase"],
    )

    if vote.hop == 1 and vote.phase == 0:
        time.sleep(1)

    # Handle reply
    if vote.hop is None:
        if vote.leader_stat != cp.node.port:
            vote.hop = None
            Message(
                opcode=OpCode.ELECTION_REPLY,
                port=cp.node.port,
                data=json.dumps(vote.__dict__),
            ).send(next_neighbour.ip, next_neighbour.port)
        else:
            if election.received.get(vote.gid) is None:
                election.received[vote.gid] = []
            received = election.received.get(vote.gid, [])
            if vote.leader_port in received:
                election.received[vote.gid] = []
                election.send_vote_to_neighbours(
                    gid=vote.gid, phase=vote.phase + 1, hop=1
                )
            else:
                received.append(vote.leader_port)

    # Handle vote
    else:
        if vote.leader_stat > cp.node.port:
            if vote.hop < 2**vote.phase:
                msg = ElectionData(
                    vote.gid,
                    vote.leader_ip,
                    vote.leader_port,
                    vote.leader_stat,
                    vote.hop + 1,
                    vote.phase,
                )
                Message(
                    opcode=OpCode.ELECTION_VOTE,
                    port=cp.node.port,
                    data=json.dumps(msg.__dict__),
                ).send(next_neighbour.ip, next_neighbour.port)
            elif 2**vote.phase > len(cp.nodes):
                logging.info(f"Invalid election state {vote}")
            else:
                vote.hop = None
                Message(
                    opcode=OpCode.ELECTION_REPLY,
                    port=cp.node.port,
                    data=json.dumps(vote.__dict__),
                ).send(previous_neighbour.ip, previous_neighbour.port)
        elif vote.leader_stat == cp.node.port:
            final = 2 ** (vote.phase + 1) > len(cp.nodes)
            if final:
                election.received = {}
                cp.make_leader(
                    cp.get_node_from_socket(f"{vote.leader_ip}:{vote.leader_port}")
                )
                Message(
                    opcode=OpCode.ELECTION_RESULT, port=vote.leader_port
                ).broadcast()

#
# def transport_handler(message: Message, ip: str, port: int, leader: bool | None = False, server: bool | None = False):
#     print(f"Receive data {message.data} from {ip}:{port}")
#     print(f"Receive data {message.data} from {ip}:{message.port}")
#     print(message)
#     Message(opcode=OpCode.TRANSPORT, data="this is the data").send(ip, 8888)

def hello_reply_handler(message: Message, ip: str, port: int):
    print("Received node state")
    print(message)
def hello_reply_handler(
    message: Message, ip: str, cp: ControlPlane, election: Election
):
    logging.debug(f"Received node state: {message.data}")

    new_nodes = [
        Node(node["ip"], node["port"], node["leader"]) for node in message.data
    ]

    for node in new_nodes:
        cp.register_heartbeat(f"{node.ip}:{node.port}")

    cp.nodes.update(set(new_nodes))

    # If the election below gets dropped due to me not having the highest port, we don't have a leader if it was not declared previously
    cp.current_leader = cp.get_node_from_socket(f"{ip}:{message.port}")

    e = Election(cp)
    e.initiate_election()

def client_hello_handler(message: Message, ip: str, cp: ControlPlane, election: Election, server: bool | None = False):
    print(f"Received HELLO from {ip}:{cp.node.port}")
    cp.register_node(Node(ip, message.port))
    print(f"Sent HELLO_REPLY to {ip}:{message.port}")
    Message(
        opcode=OpCode.HELLO_REPLY,
        port=cp.node.port,
        data=list(map(lambda node: node.__dict__, cp.nodes)),
    ).send(ip, message.port)

def hello_handler(message: Message, ip: str, cp: ControlPlane, election: Election,
                  # app_state: ApplicationState
                  ):
    cp.register_node(Node(ip, message.port))
    # print(f"Received HELLO from {ip}:{port}")
    # print(f"Received HELLO from {ip}:{message.port}")
    # print(f"Sent HELLO_REPLY to {ip}:{message.port}")
    if cp.current_leader == None or cp.node.leader == True:
        Message(
            opcode=OpCode.HELLO_REPLY,
            port=cp.node.port,
            data=list(map(lambda node: node.__dict__, cp.nodes)),
        ).send(ip, message.port)
        # Message (
        #     opcode = OpCode.APPLICATIONS_STATE,
        #     port=cp.node.port,
        #     data=json.dumps(app_state.__dict__)
        #)
