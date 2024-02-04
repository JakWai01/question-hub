from dataclasses import dataclass


@dataclass
class Node:
    ip: str
    port: int
    leader: bool
    server: bool

    def __init__(cls, ip: str, port: int, leader: bool | None = False,
                 server: bool | None = False
                 ):
        cls.ip = ip
        cls.port = port
        cls.leader = leader
        cls.server = server
        cls.received = {}

    def __hash__(cls):
        return hash(f"{cls.ip}:{cls.port}")
