import socket
import json
from ipaddress import IPv4Interface
import netifaces
import time
from enum import Enum, unique
from threading import Thread

class OpCode(str, Enum):
    SERVER_HELLO = "server_hello"

class Message():
    def __init__(self, opcode: OpCode, data: bytes | None = None):
        self.opcode = opcode
        self.data = data

    def marshal(self):
        return bytes(json.dumps(self.__dict__), "UTF-8")

    @staticmethod
    def unmarshal(data_b: bytes) -> "Message":
        data_str = data_b.decode("UTF-8")
        payload = json.loads(data_str)
        print(payload)
        return Message(OpCode(payload.get("opcode")), payload.get("data"))

    def broadcast(self, timeout=0) -> tuple["Message", str, str]:
        return send(self.marshal(), timeout=timeout)

def send(payload: bytes, address: tuple[str, int] | None = None, timeout=0) -> tuple[Message, str, str] | None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if address is None:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        address = (BROADCAST_IP, BROADCAST_PORT)

    sock.sendto(payload, address)

    response = None
    start = time.time()
    sock.settimeout(timeout)
    while time.time() - start < timeout:
        try:
            data, (ip, port) = sock.recvfrom(1024)
        except TimeoutError:
            break

        if data:
            msg = Message(command=None, data=data)
            response = msg, ip, port
            break

    sock.close()
    return response
    

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

def register_listener(callback):
    listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_socket.bind(('', BROADCAST_PORT))

    try:
        while True:
            data, (ip, port) = listen_socket.recvfrom(1024)
            if data:
                message = data.decode("utf-8")
                callback(message, ip, port)
    except KeyboardInterrupt:
        listen_socket.close()
        exit(0)

def callback(message, ip, port):
    print(f"Broadcast message received: {message}") 
       
def main():
    threads = []
    
    listener_thread = Thread(target=register_listener, args=(callback,))
    listener_thread.start()
    threads.append(listener_thread)

    Message(OpCode.SERVER_HELLO).broadcast()

    for thread in threads:
        thread.join()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit(0)
