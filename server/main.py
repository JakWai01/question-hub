import argparse
import json
from threading import Thread
import logging
import time
import node
import control_plane
import api
from network import Message, OpCode, INTERFACE
from election import Election
from application_state import ApplicationState
import socket

def find_available_port(start_port, max_attempts=10):
    for _ in range(max_attempts):
        try:
            # Create a socket to check if the port is available
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', start_port))
            return start_port
        except socket.error:
            start_port += 1

def main():
    parser = argparse.ArgumentParser(prog="Server")

    parser.add_argument("--port", default=9765, type=int)
    parser.add_argument("--delay", default=1, type=int)
    parser.add_argument("--loglevel", default="INFO", type=str)

    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    threads = []

    cp = control_plane.ControlPlane()
    cp.node = node.Node(INTERFACE.ip.compressed, args.port, False)
    cp.register_node(cp.node)
    cp.register_heartbeat(f"{cp.node.ip}:{cp.node.port}")
    cp.count_heartbeats_sent(f"{cp.node.ip}:{cp.node.port}")

    election = Election(cp)

    app_state = ApplicationState()

    listener_thread = Thread(
        target=api.broadcast_target, args=(api.message_handler, cp, election, app_state)
    )
    listener_thread.start()
    threads.append(listener_thread)

    uni_thread = Thread(
        target=api.unicast_target,
        args=(api.message_handler, args.port, cp, election, app_state),
    )
    uni_thread.start()
    threads.append(uni_thread)

    heartbeat_thread = Thread(
        target=api.heartbeat_target,
        args=(api.message_handler, args.delay, cp, election, app_state),
    )
    heartbeat_thread.start()
    threads.append(heartbeat_thread)
    MCAST_GRP = "224.1.1.1"
    MCAST_PORT = 11111

    Message(opcode=OpCode.HEARTBEAT, port=cp.node.port).send(MCAST_GRP, MCAST_PORT)

    Message(OpCode.HELLO, port=cp.node.port, data=json.dumps(cp.node.__dict__)).broadcast(2)

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
