from enum import Enum
from ipaddress import IPv4Interface
import netifaces
import json
import socket
import logging

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


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


HOSTNAME = socket.gethostname()
INTERFACE = get_network_interface()

BROADCAST_PORT = 34567
BROADCAST_IP = str(INTERFACE.network.broadcast_address)


class OpCode(str, Enum):
    HELLO_SERVER = "hello_server"
    HELLO_REPLY = "hello_reply"
    HEARTBEAT = "heartbeat"

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


def send(payload: bytes, address: tuple[str, int] | None = None, timeout=0):
    if address is None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        address = (BROADCAST_IP, BROADCAST_PORT)

    msg = json.loads(payload)

    if msg["opcode"] != "heartbeat":
        logging.info(
            f"Sending message of type {msg['opcode']} to {address[0]}:{address[1]}"
        )

    sock.sendto(payload, address)
