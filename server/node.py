from dataclasses import dataclass
from uuid import uuid4

@dataclass
class Node:
    ip: str
    port: int
    leader: bool
    uuid: str

    def __init__(self, ip: str, port: int, leader: bool | None = False, uuid=None):
        self.ip = ip
        self.port = port
        self.leader = leader
        self.received = {}
        self.uuid = str(uuid4()) if uuid==None else uuid

    def __hash__(self):
        return hash(f"{self.ip}:{self.port}")
