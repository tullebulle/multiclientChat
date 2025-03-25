"""
Mock Network for Testing Raft

This module provides a mock network layer for testing multi-node Raft clusters
without requiring actual network connections. It simulates network communication
between nodes and allows for testing leader election, log replication, and 
fault tolerance scenarios.
"""

import logging
import threading
import time
import random
from typing import Dict, List, Tuple, Callable, Any, Optional, Set
from queue import Queue, Empty

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class NetworkMessage:
    """
    Represents a message sent between nodes in the mock network.
    """
    
    def __init__(self, sender: str, receiver: str, rpc_type: str, request: Any):
        """
        Initialize a network message.
        
        Args:
            sender: ID of the sending node
            receiver: ID of the receiving node
            rpc_type: Type of RPC call (e.g., 'RequestVote', 'AppendEntries')
            request: The RPC request data
        """
        self.sender = sender
        self.receiver = receiver
        self.rpc_type = rpc_type
        self.request = request
        self.timestamp = time.time()


class MockNetwork:
    """
    Simulates a network for Raft nodes to communicate without actual network connections.
    
    This class maintains message queues for each node and delivers messages with
    configurable latency and packet loss to simulate real network conditions.
    """
    
    def __init__(self, node_ids: List[str], delivery_latency_range: Tuple[float, float] = (0.01, 0.05),
                 packet_loss_probability: float = 0.0):
        """
        Initialize the mock network.
        
        Args:
            node_ids: List of node IDs in the network
            delivery_latency_range: Range of random latency for message delivery in seconds
            packet_loss_probability: Probability of a message being lost (0.0 to 1.0)
        """
        self.node_ids = node_ids
        self.delivery_latency_range = delivery_latency_range
        self.packet_loss_probability = packet_loss_probability
        
        # Message queues for each node
        self.message_queues: Dict[str, Queue] = {node_id: Queue() for node_id in node_ids}
        
        # Disconnected nodes (to simulate network partitions)
        self.disconnected_nodes: Set[str] = set()
        
        # Message handlers for each node
        self.message_handlers: Dict[str, Dict[str, Callable]] = {}
        
        # Message delivery thread
        self.delivery_thread = threading.Thread(target=self._deliver_messages, daemon=True)
        self.stop_delivery = threading.Event()
        self.delivery_thread.start()
        
        logging.info(f"Mock network initialized with nodes: {node_ids}")
    
    def register_handler(self, node_id: str, rpc_type: str, handler: Callable):
        """
        Register a message handler for a node.
        
        Args:
            node_id: ID of the node
            rpc_type: Type of RPC to handle
            handler: Function to call when a message is received
        """
        if node_id not in self.message_handlers:
            self.message_handlers[node_id] = {}
        
        self.message_handlers[node_id][rpc_type] = handler
        logging.debug(f"Registered {rpc_type} handler for node {node_id}")
    
    def send_message(self, sender: str, receiver: str, rpc_type: str, request: Any):
        """
        Send a message from one node to another.
        
        Args:
            sender: ID of the sending node
            receiver: ID of the receiving node
            rpc_type: Type of RPC call
            request: The RPC request data
            
        Returns:
            bool: True if message was queued, False otherwise
        """
        if sender not in self.node_ids or receiver not in self.node_ids:
            logging.error(f"Cannot send message: Invalid node ID {sender} or {receiver}")
            return False
        
        if sender in self.disconnected_nodes or receiver in self.disconnected_nodes:
            logging.info(f"Message from {sender} to {receiver} dropped: Node disconnected")
            return False
        
        message = NetworkMessage(sender, receiver, rpc_type, request)
        self.message_queues[receiver].put(message)
        logging.debug(f"Queued {rpc_type} message from {sender} to {receiver}")
        return True
    
    def disconnect_node(self, node_id: str):
        """
        Disconnect a node from the network (simulate failure).
        
        Args:
            node_id: ID of the node to disconnect
        """
        if node_id in self.node_ids:
            self.disconnected_nodes.add(node_id)
            logging.info(f"Node {node_id} disconnected from network")
    
    def reconnect_node(self, node_id: str):
        """
        Reconnect a previously disconnected node.
        
        Args:
            node_id: ID of the node to reconnect
        """
        if node_id in self.disconnected_nodes:
            self.disconnected_nodes.remove(node_id)
            logging.info(f"Node {node_id} reconnected to network")
    
    def is_connected(self, node_id: str) -> bool:
        """
        Check if a node is connected to the network.
        
        Args:
            node_id: ID of the node to check
            
        Returns:
            bool: True if connected, False otherwise
        """
        return node_id in self.node_ids and node_id not in self.disconnected_nodes
    
    def _deliver_messages(self):
        """
        Background thread to deliver messages with simulated latency.
        """
        while not self.stop_delivery.is_set():
            # Check each node's message queue
            for node_id, queue in self.message_queues.items():
                try:
                    # Non-blocking check for messages
                    message = queue.get_nowait()
                    
                    # Simulate packet loss
                    if random.random() < self.packet_loss_probability:
                        logging.debug(f"Message from {message.sender} to {message.receiver} lost")
                        queue.task_done()
                        continue
                    
                    # Simulate network latency
                    latency = random.uniform(*self.delivery_latency_range)
                    time.sleep(latency)
                    
                    # Deliver the message if the node is still connected
                    if (node_id not in self.disconnected_nodes and 
                        message.sender not in self.disconnected_nodes):
                        self._handle_message(message)
                    
                    queue.task_done()
                except Empty:
                    # No messages in queue, continue to next node
                    pass
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.01)
    
    def _handle_message(self, message: NetworkMessage):
        """
        Handle delivery of a message to its destination.
        
        Args:
            message: The message to deliver
        """
        node_id = message.receiver
        rpc_type = message.rpc_type
        
        if node_id in self.message_handlers and rpc_type in self.message_handlers[node_id]:
            try:
                handler = self.message_handlers[node_id][rpc_type]
                handler(message.sender, message.request)
                logging.debug(f"Delivered {rpc_type} from {message.sender} to {node_id}")
            except Exception as e:
                logging.error(f"Error handling message {rpc_type} to {node_id}: {e}")
        else:
            logging.warning(f"No handler for {rpc_type} on node {node_id}")
    
    def shutdown(self):
        """
        Shut down the mock network and clean up resources.
        """
        self.stop_delivery.set()
        self.delivery_thread.join(timeout=1.0)
        logging.info("Mock network shut down")


class MockRpcClient:
    """
    Mock RPC client for a Raft node to use instead of actual gRPC calls.
    
    This class simulates the client side of RPC calls by sending messages
    through the mock network.
    """
    
    def __init__(self, node_id: str, peer_id: str, network: MockNetwork):
        """
        Initialize the mock RPC client.
        
        Args:
            node_id: ID of this node (the client)
            peer_id: ID of the peer node to send RPCs to
            network: The mock network to use for communication
        """
        self.node_id = node_id
        self.peer_id = peer_id
        self.network = network
    
    def request_vote(self, request):
        """
        Send a RequestVote RPC to the peer.
        
        Args:
            request: The RequestVote request data
            
        Returns:
            Mock response or raises an exception if disconnected
        """
        if not self.network.is_connected(self.node_id) or not self.network.is_connected(self.peer_id):
            raise Exception("Node is disconnected")
        
        response = {'term': 0, 'vote_granted': False}
        
        # TODO: In a real implementation, we would wait for a response
        # For now, simply send the message
        self.network.send_message(self.node_id, self.peer_id, 'RequestVote', request)
        
        return response
    
    def append_entries(self, request):
        """
        Send an AppendEntries RPC to the peer.
        
        Args:
            request: The AppendEntries request data
            
        Returns:
            Mock response or raises an exception if disconnected
        """
        if not self.network.is_connected(self.node_id) or not self.network.is_connected(self.peer_id):
            raise Exception("Node is disconnected")
        
        response = {'term': 0, 'success': False, 'match_index': 0}
        
        # TODO: In a real implementation, we would wait for a response
        # For now, simply send the message
        self.network.send_message(self.node_id, self.peer_id, 'AppendEntries', request)
        
        return response


# Helper class to represent a MockRaftNode for testing
class MockRaftNode:
    """
    Simple mock implementation of a Raft node for testing.
    """
    
    def __init__(self, node_id: str, network: MockNetwork, initial_term: int = 0):
        """
        Initialize the mock Raft node.
        
        Args:
            node_id: ID of this node
            network: The mock network for communication
            initial_term: Initial term number
        """
        self.node_id = node_id
        self.network = network
        self.current_term = initial_term
        self.voted_for = None
        self.log = []
        self.commit_index = 0
        self.last_applied = 0
        self.state = "FOLLOWER"
        self.leader_id = None
        
        # For tracking votes received during an election
        self.votes_received = set()
        
        # Register message handlers
        network.register_handler(node_id, 'RequestVote', self._handle_request_vote)
        network.register_handler(node_id, 'RequestVoteResponse', self._handle_request_vote_response)
        network.register_handler(node_id, 'AppendEntries', self._handle_append_entries)
        network.register_handler(node_id, 'AppendEntriesResponse', self._handle_append_entries_response)
    
    def _handle_request_vote(self, sender_id: str, request: Dict):
        """
        Handle a RequestVote RPC from another node.
        
        Args:
            sender_id: ID of the sending node
            request: The RequestVote request data
        """
        term = request['term']
        candidate_id = request['candidate_id']
        
        # If the term is higher, update our term and convert to follower
        if term > self.current_term:
            self.current_term = term
            self.state = "FOLLOWER"
            self.voted_for = None
        
        vote_granted = False
        
        # Vote if we haven't voted yet in this term and the candidate's log is at least as up-to-date
        if (term == self.current_term and 
            (self.voted_for is None or self.voted_for == candidate_id)):
            # In a full implementation, we would check log completeness
            vote_granted = True
            self.voted_for = candidate_id
        
        response = {
            'term': self.current_term,
            'vote_granted': vote_granted
        }
        
        # Send the response
        self.network.send_message(self.node_id, sender_id, 'RequestVoteResponse', response)
    
    def _handle_request_vote_response(self, sender_id: str, response: Dict):
        """
        Handle a response to RequestVote RPC.
        
        Args:
            sender_id: ID of the node that sent the response
            response: The response data
        """
        term = response['term']
        vote_granted = response['vote_granted']
        
        # If term is higher, update term and revert to follower
        if term > self.current_term:
            self.current_term = term
            self.state = "FOLLOWER"
            self.voted_for = None
            return
        
        # Only process responses if we're still a candidate
        if self.state != "CANDIDATE" or term != self.current_term:
            return
        
        # Count the vote
        if vote_granted:
            self.votes_received.add(sender_id)
            
            # If we have a majority, become leader
            if len(self.votes_received) + 1 > len(self.network.node_ids) // 2:
                self.state = "LEADER"
                self.leader_id = self.node_id
                logging.info(f"Node {self.node_id} won election for term {self.current_term}")
                
                # Send heartbeat immediately to establish authority
                self.send_heartbeat()
    
    def _handle_append_entries(self, sender_id: str, request: Dict):
        """
        Handle an AppendEntries RPC from another node.
        
        Args:
            sender_id: ID of the sending node
            request: The AppendEntries request data
        """
        term = request['term']
        leader_id = request['leader_id']
        
        # If the term is higher, update our term and convert to follower
        if term > self.current_term:
            self.current_term = term
            self.state = "FOLLOWER"
            self.voted_for = None
        
        success = False
        match_index = 0
        
        # Accept the entry if the term is valid
        if term == self.current_term:
            self.leader_id = leader_id
            self.state = "FOLLOWER"
            success = True
            
            # Process log entries
            prev_log_index = request.get('prev_log_index', 0)
            prev_log_term = request.get('prev_log_term', 0)
            entries = request.get('entries', [])
            leader_commit = request.get('leader_commit', 0)
            
            # Check if we have the previous log entry with matching term
            prev_log_match = (prev_log_index == 0) or (
                prev_log_index <= len(self.log) and 
                (prev_log_index == 0 or self.log[prev_log_index - 1]['term'] == prev_log_term)
            )
            
            if prev_log_match:
                # Add new entries
                if entries:
                    # Remove conflicting entries
                    if prev_log_index < len(self.log):
                        self.log = self.log[:prev_log_index]
                    
                    # Append new entries
                    self.log.extend(entries)
                
                # Update commit index
                if leader_commit > self.commit_index:
                    self.commit_index = min(leader_commit, len(self.log))
                
                match_index = prev_log_index + len(entries)
                success = True
            else:
                # Log inconsistency
                success = False
                match_index = 0
        
        response = {
            'term': self.current_term,
            'success': success,
            'match_index': match_index
        }
        
        # Send the response
        self.network.send_message(self.node_id, sender_id, 'AppendEntriesResponse', response)
    
    def _handle_append_entries_response(self, sender_id: str, response: Dict):
        """
        Handle a response to AppendEntries RPC.
        
        Args:
            sender_id: ID of the node that sent the response
            response: The response data
        """
        term = response['term']
        success = response['success']
        match_index = response['match_index']
        
        # If term is higher, update term and revert to follower
        if term > self.current_term:
            self.current_term = term
            self.state = "FOLLOWER"
            self.voted_for = None
            self.leader_id = None
            return
        
        # Only process if we're still the leader
        if self.state != "LEADER" or term != self.current_term:
            return
        
        # Update match index for this follower
        if success:
            # In a real implementation, this would update next_index and match_index
            pass
    
    def start_election(self):
        """
        Start an election by sending RequestVote RPCs to all peers.
        """
        self.current_term += 1
        self.state = "CANDIDATE"
        self.voted_for = self.node_id
        self.votes_received = set()  # Reset votes received
        
        # Vote for self
        self.votes_received.add(self.node_id)
        
        # Create a RequestVote request
        request = {
            'term': self.current_term,
            'candidate_id': self.node_id,
            'last_log_index': len(self.log) - 1 if self.log else 0,
            'last_log_term': self.log[-1]['term'] if self.log else 0
        }
        
        # Send RequestVote RPCs to all peers
        for peer_id in self.network.node_ids:
            if peer_id != self.node_id:
                self.network.send_message(self.node_id, peer_id, 'RequestVote', request)
        
        # If sole node (no peers), become leader immediately
        if len(self.network.node_ids) == 1:
            self.state = "LEADER"
            self.leader_id = self.node_id
            logging.info(f"Single node {self.node_id} became leader for term {self.current_term}")
    
    def send_heartbeat(self):
        """
        Send heartbeat (empty AppendEntries RPCs) to all peers.
        """
        if self.state != "LEADER":
            return
        
        # Create an AppendEntries request with actual entries if there are any
        for peer_id in self.network.node_ids:
            if peer_id != self.node_id:
                # Send all log entries to each follower
                request = {
                    'term': self.current_term,
                    'leader_id': self.node_id,
                    'prev_log_index': 0,  # For simplicity, always start from beginning
                    'prev_log_term': 0,   # For simplicity, use term 0 for beginning
                    'entries': self.log,  # Send all log entries
                    'leader_commit': self.commit_index
                }
                
                self.network.send_message(self.node_id, peer_id, 'AppendEntries', request) 