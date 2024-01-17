from node import Node
import time
import logging

class ControlPlane:
    def __init__(self):
        self._node: Node = None
        self._nodes: set[Node] = set()
        self._node_heartbeats = {}
        self.current_leader: Node = None
   
    @property
    def nodes(self):
        return self._nodes

    def register_heartbeat(self, socket: str):
        self._node_heartbeats[socket] = int(time.time())

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
        if self.current_leader is not None:
            self.current_leader.leader = False

        node.leader = True
        self.current_leader = node

    # TODO: Only take node as an argument
    # TODO: One of those needs to be the own node
    def get_next_neighbour(self, sender_node: Node):
        sender_ring_index = self.get_nodes_sorted().index(f"{sender_node.ip}:{sender_node.port}")

        if sender_ring_index < self.ring_index(self.node):
            return self.right_neighbour(self.node)
        else:
            return self.left_neighbour(self.node)

    # TODO: Only take node as an argument
    def get_previous_neighbour(self, sender_node: Node):
        sender_ring_index = self.get_nodes_sorted().index(f"{sender_node.ip}:{sender_node.port}")
        
        if sender_ring_index < self.ring_index(self.node):
            return self.left_neighbour(self.node)
        else:
            return self.right_neighbour(self.node)
    
    def ring_index(self, node: Node):
        return self.get_nodes_sorted().index(f"{node.ip}:{node.port}")

    def left_neighbour(self, node: Node):
        left_neighbour = self.get_nodes_sorted()[(self.ring_index(node) - 1) % len(self.nodes)]
        return self.get_node_from_socket(left_neighbour)
    
    def right_neighbour(self, node: Node):
        right_neighbour = self.get_nodes_sorted()[(self.ring_index(node) + 1) % len(self.nodes)]
        return self.get_node_from_socket(right_neighbour)
         