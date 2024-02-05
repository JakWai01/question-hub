from network import Message, OpCode
import socket
from network import INTERFACE, BROADCAST_PORT
import logging
import time
from node import Node
import json
# from application_state import ApplicationState, Question, Vote

# def application_state_handler(message: Message, ip: str, cp: ControlPlane, election: Election, app_state: ApplicationState):
#     msg = json.loads(message.data)
#
#     print(msg)

# Vote for an existing question. If the leader does not know about the question, the question does not exist. 
# Each question is assigned a unique UUID for identification purposes
def vote_request_handler(message: Message, ip: str, 
                         # app_state: ApplicationState
                         ):
    msg = json.loads(message.data)
    #question = app_state.get_question_from_uuid(msg.uuid)

    vote = Vote(msg.socket, msg.uuid)

    question.toggle_vote(vote)
    Message(opcode=OpCode.VOTE, port=cp.node.port, data=json.dumps(vote.__dict__)).broadcast()

# Since only the leader handles the request, the other servers also need to receive the update. This happens via the broadcast.
def vote_handler(message: Message, ip: str,
                 # app_state: ApplicationState
                 ):
    msg = json.loads(message.data)
    #question = app_state.get_question_from_uuid(msg.uuid)

    vote = Vote(msg.socket, msg.uuid)

    question.toggle_vote(vote)

# Post a new question to the application
def question_request_handler(message: Message, ip: str,
                             #app_state: ApplicationState
                             ):
    msg = json.loads(message.data)
    
    question = Question(msg.text)
    #app_state.add_question(question)

    Message(opcode=OpCode.QUESTION, port=cp.node.port, data=json.dumps(question.__dict__)).broadcast()

def question_handler(message: Message, ip: str,
                     #app_state: ApplicationState
                     ):
    msg = json.loads(message.data)
    
    question = Question(msg.text)
    #app_state.add_question(question)

def heartbeat_handler(message: Message, ip: str):
    print(f"{ip}:{message.port}")


def broadcast_target(callback):
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

                callback(msg, ip)
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
                logging.debug(f"Unicast message received: {msg.opcode}")
                callback(msg, ip)
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

            time.sleep(delay)

    except KeyboardInterrupt:
        exit(0)


def message_handler(message: Message, ip: str,
                    #app_state: ApplicationState
                    ):
    # if ip == cp.node.ip and message.port == cp.node.port:
    #     return
    print("some message received")
    print(message.opcode)

    if message.opcode is not OpCode.HEARTBEAT:
        logging.info(
            f"Received message of type {message.opcode.value} from {ip}:{message.port}"
        )

    if message.opcode is OpCode.HELLO:
        hello_handler(message, ip)
    elif message.opcode is OpCode.HELLO_REPLY:
        hello_reply_handler(message, ip
                            #app_state
                            )
    elif message.opcode is OpCode.HELLO_SERVER:
        hello_handler(message, ip)
    elif message.opcode is OpCode.HELLO_CLIENT:
        client_hello_handler(message, ip)
    elif message.opcode is OpCode.HEARTBEAT:
        heartbeat_handler(message, ip)
    elif message.opcode is OpCode.ELECTION_RESULT:
        election_result_handler(message, ip)
    elif message.opcode is OpCode.QUESTION_REQUEST:
        question_request_handler(message, ip
                                 #app_state
                                 )
    elif message.opcode is OpCode.VOTE_REQUEST:
        vote_request_handler(message, ip
                             #app_state
                             )
    elif message.opcode is OpCode.VOTE:
        vote_handler(message, ip
                     #app_state
                     )
    elif message.opcode is OpCode.QUESTION:
        question_handler(message, ip
                         #app_state
                         )
    # elif message.opcode is OpCode.APPLICATION_STATE:
    #     application_state_handler(message, ip, cp, election, app_state)
    else:
        return

#
# def transport_handler(message: Message, ip: str, port: int, leader: bool | None = False, server: bool | None = False):
#     print(f"Receive data {message.data} from {ip}:{port}")
#     print(f"Receive data {message.data} from {ip}:{message.port}")
#     print(message)
#     Message(opcode=OpCode.TRANSPORT, data="this is the data").send(ip, 8888)

# def hello_reply_handler(message: Message, ip: str, port: int):
#     print("Received node state")
#     print(message)
def hello_reply_handler(
    message: Message, ip: str
):
    logging.debug(f"Received node state: {message.data}")
    print ("Hello reply received from", ip,":", message.port, "with message", message.data)

    new_nodes = [
        Node(node["ip"], node["port"], node["leader"]) for node in message.data
    ]

    #for node in new_nodes:
        #cp.register_heartbeat(f"{node.ip}:{node.port}")

    #cp.nodes.update(set(new_nodes))

    # If the election below gets dropped due to me not having the highest port, we don't have a leader if it was not declared previously
    #cp.current_leader = cp.get_node_from_socket(f"{ip}:{message.port}")

    #e = Election(cp)
    #e.initiate_election()

def election_result_handler(
    message: Message, ip: str
):
    print("switch messages to this port", message.port)

def client_hello_handler(message: Message, ip: str, server: bool | None = False):
    #print(f"Received HELLO from {ip}:{cp.node.port}")
    #cp.register_node(Node(ip, message.port))
    print(f"Sent HELLO_REPLY to {ip}:{message.port}")
    # Message(
    #     opcode=OpCode.HELLO_REPLY,
    #     port=cp.node.port,
    #     data=list(map(lambda node: node.__dict__, cp.nodes)),
    # ).send(ip, message.port)

def hello_handler(message: Message, ip: str
                  # app_state: ApplicationState
                  ):
    print("Received")
    # print(f"Received HELLO from {ip}:{port}")
    # print(f"Received HELLO from {ip}:{message.port}")
    # print(f"Sent HELLO_REPLY to {ip}:{message.port}")
    # if cp.current_leader == None or cp.node.leader == True:
    #     Message(
    #         opcode=OpCode.HELLO_REPLY,
    #         port=cp.node.port,
    #         data=list(map(lambda node: node.__dict__, cp.nodes)),
    #     ).send(ip, message.port)
        # Message (
        #     opcode = OpCode.APPLICATIONS_STATE,
        #     port=cp.node.port,
        #     data=json.dumps(app_state.__dict__)
        #)
