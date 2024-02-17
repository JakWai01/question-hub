from node import Node
import time
import logging


class ControlPlane:
    def __init__(self):
        self._node: Node = None
        self._nodes: set[Node] = set()
        self._node_heartbeats = {}
        self._node_heartbeats_sent = {}
        self._node_heartbeats_received = {}
        self.current_leader: Node = None

    @property
    def nodes(self):
        return self._nodes

    def register_heartbeat(self, socket: str):
        self._node_heartbeats[socket] = int(time.time())

    def count_heartbeats_sent(self, socket: str):
        if socket in self._node_heartbeats:
            if socket in self._node_heartbeats_sent:
                self._node_heartbeats_sent[socket] += 1
            else:
                self._node_heartbeats_sent[socket] = 1

    def count_heartbeats_received(self, socket: str):
        if socket in self._node_heartbeats:
            if socket in self._node_heartbeats_received:
                self._node_heartbeats_received[socket] += 1
            else:
                self._node_heartbeats_received[socket] = 1

    @nodes.setter
    def nodes(self, new_nodes: set[Node]):
        self._nodes = new_nodes

    @property
    def node(self):
        return self._node

    @node.setter
    def node(self, node: Node):
        self._node = node

    def register_node(self, node: Node):
        logging.info(f"Registering node {node}")
        self._nodes.add(node)

    def remove_node(self, node: Node):
        self._nodes.remove(node)

    def get_node_from_socket(self, socket: str) -> Node | None:
        ip, port = socket.split(":")
        for node in self.nodes:
            if node.ip == ip and node.port == int(port):
                return node
            else:
                continue

    def get_leader(self) -> Node | None:
        return self.current_leader

    def get_nodes_sorted(self) -> list[Node]:
        return sorted(list(self._node_heartbeats))

    def make_leader(self, node: Node):
        logging.info(f"Node {node.ip}:{node.port} has been appointed the new leader")
        if self.current_leader is not None:
            self.current_leader.leader = False

        node.leader = True
        self.current_leader = node

    def get_next_neighbour(self, sender_node: Node):
        sender_ring_index = self.get_nodes_sorted().index(
            f"{sender_node.ip}:{sender_node.port}"
        )

        if (
            self.ring_index(self.node) == 0
            and sender_ring_index != len(self.get_nodes_sorted()) - 1
        ):
            return self.get_node_from_socket(
                self.get_nodes_sorted()[len(self.get_nodes_sorted()) - 1]
            )
        elif (
            self.ring_index(self.node) == len(self.get_nodes_sorted()) - 1
            and sender_ring_index != 0
        ):
            return self.get_node_from_socket(self.get_nodes_sorted()[0])
        elif (
            self.ring_index(self.node) == 0
            and sender_ring_index == len(self.get_nodes_sorted()) - 1
        ):
            return self.right_neighbour(self.node)
        elif (
            self.ring_index(self.node) == len(self.get_nodes_sorted()) - 1
            and sender_ring_index == 0
        ):
            return self.left_neighbour(self.node)
        elif sender_ring_index < self.ring_index(self.node):
            return self.right_neighbour(self.node)
        else:
            return self.left_neighbour(self.node)

    def ring_index(self, node: Node):
        return self.get_nodes_sorted().index(f"{node.ip}:{node.port}")

    def left_neighbour(self, node: Node):
        logging.info(f"Nodes: {self.nodes}")
        left_neighbour = self.get_nodes_sorted()[
            (self.ring_index(node) - 1) % len(self.nodes)
        ]
        return self.get_node_from_socket(left_neighbour)

    def right_neighbour(self, node: Node):
        logging.info(f"Nodes: {self.nodes}")
        right_neighbour = self.get_nodes_sorted()[
            (self.ring_index(node) + 1) % len(self.nodes)
        ]
        return self.get_node_from_socket(right_neighbour)
