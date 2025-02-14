import uuid
from control_plane import ControlPlane
import logging
from network import Message, OpCode
import json


class ElectionData:
    def __init__(
        self,
        gid: str,
        leader_ip: str,
        leader_port: int,
        leader_stat: int,
        hop: int | None,
        phase: int,
    ):
        self.gid = gid
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
            node = self.cp.get_node_from_socket(
                next(iter(self.cp._node_heartbeats.keys()))
            )
            self.make_leader(node)
            return

        gid = str(uuid.uuid4())

        self.send_vote_to_neighbours(gid, phase=0, hop=1)

    def send_vote_to_neighbours(
        self, gid: str, phase: int | None = 0, hop: int | None = 1
    ):
        msg = ElectionData(
            gid, self.cp.node.ip, self.cp.node.port, self.cp.node.uuid, hop, phase
        )

        right_neighbour = self.cp.right_neighbour(self.cp.node)
        left_neighbour = self.cp.left_neighbour(self.cp.node)

        for neighbour in [left_neighbour, right_neighbour]:
            Message(
                opcode=OpCode.ELECTION_VOTE,
                port=self.cp.node.port,
                data=json.dumps(msg.__dict__),
            ).send(neighbour.ip, neighbour.port)
