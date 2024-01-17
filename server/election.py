from control_plane import ControlPlane
from node import Node
import logging
from network import Message, OpCode
import json

class ElectionData:
    def __init__(self, leader_ip: str, leader_port: int, leader_stat: int, hop: int | None, phase: int):
        self.leader_ip = leader_ip
        self.leader_port = leader_port
        self.leader_stat = leader_stat
        self.hop = hop
        self.phase = phase

class Election:
    cp: ControlPlane
    received: dict[str, list[tuple[int, float]]]

    def __init__(self, cp: ControlPlane):
        self.cp = cp
        self.received = {}
       
    
    def initiate_election(self):
        logging.info("Starting a new election")

        if len(self.cp._node_heartbeats) == 0:
            logging.info("We are the only node")
            node = self.cp.get_node_from_socket(next(iter(self.cp._node_heartbeats.keys())))
            self.make_leader(node)
            return

        self.send_vote_to_neighbours(phase=-1, hop=1)

    def send_vote_to_neighbours(self, phase: int | None = 0 , hop: int | None = 1):
        msg = ElectionData(self.cp.node.ip, self.cp.node.port, self.cp.node.port, hop, phase)

        right_neighbour = self.cp.right_neighbour(self.cp.node)
        left_neighbour = self.cp.left_neighbour(self.cp.node)

        # TODO: We are missing the node state here
        print(right_neighbour)
        print(left_neighbour)
        print(self.cp.nodes)

        for neighbour in [left_neighbour, right_neighbour]:
            Message(opcode=OpCode.ELECTION, port=self.cp.node.port, data=json.dumps(msg.__dict__)).send(neighbour.ip, neighbour.port)
