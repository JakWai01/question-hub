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

        right_neighbour = self.right_neighbour(self.cp.node)
        left_neighbour = self.left_neighbour(self.cp.node)

        for neighbour in [left_neighbour, right_neighbour]:
            Message(opcode=OpCode.ELECTION, port=self.cp.node.port, data=json.dumps(msg.__dict__)).send(neighbour.ip, neighbour.port)

    def get_next_neighbour(self, node: Node, socket: str):
        socket_ring_index = cp.get_nodes_sorted().index(socket)

        if socket_ring_index < node.ring_index:
            return node.left_neighbour
        else:
            return node.right_neighbour

    def get_previous_neighbour(self, socket: str):
        socket_ring_index = cp.get_nodes_sorted().index(socket)

        if socket_ring_index < self.ring_index:
            return self.right_neighbour
        else:
            return self.left_neighbour
    
    def ring_index(self, node: Node):
        return self.cp.get_nodes_sorted().index(f"{node.ip}:{node.port}")

    def left_neighbour(self, node: Node):
        left_neighbour = self.cp.get_nodes_sorted()[(self.ring_index(node) - 1) % len(self.cp.nodes)]
        return self.cp.get_node_from_socket(left_neighbour)
    
    def right_neighbour(self, node: Node):
        right_neighbour = self.cp.get_nodes_sorted()[(self.ring_index(node) + 1) % len(self.cp.nodes)]
        return self.cp.get_node_from_socket(right_neighbour)
        
