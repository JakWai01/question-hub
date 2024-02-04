import argparse
from threading import Thread
import logging
import node
import control_plane
import api
from network import Message, OpCode, INTERFACE
from election import Election


def main():
    parser = argparse.ArgumentParser(prog="Server")

    parser.add_argument("--port", default=8765, type=int)
    parser.add_argument("--delay", default=1, type=int)
    parser.add_argument("--loglevel", default="INFO", type=str)


    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    threads = []

    cp = control_plane.ControlPlane()
    cp.node = node.Node(INTERFACE.ip.compressed, args.port, False)
    cp.register_node(cp.node)
    cp.register_heartbeat(f"{cp.node.ip}:{cp.node.port}")

    election = Election(cp)

    listener_thread = Thread(
        target=api.broadcast_target, args=(api.message_handler, cp, election)
    )
    listener_thread.start()
    threads.append(listener_thread)

    uni_thread = Thread(
        target=api.unicast_target,
        args=(api.message_handler, cp.node.port, cp, election),
    )
    uni_thread.start()
    threads.append(uni_thread)

    heartbeat_thread = Thread(
        target=api.heartbeat_target,
        args=(api.message_handler, args.delay, cp, election),
    )
    heartbeat_thread.start()
    threads.append(heartbeat_thread)

    #Message(OpCode.HELLO_SERVER, port=args.port).broadcast(2)

    Message(OpCode.HELLO, port=cp.node.port).broadcast(2)

    for thread in threads:
        thread.join()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
