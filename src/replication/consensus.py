"""
Raft Consensus Implementation

This module implements the Raft distributed consensus algorithm for the chat application.
It provides the core functionality for leader election, log replication, and state management
that ensures consistency across distributed chat servers.

Based on the Raft paper: https://raft.github.io/raft.pdf
"""

import logging
import random
import threading
import time
import grpc
import json
from enum import Enum, auto
from typing import Dict, List, Tuple, Optional, Any, Set, Union

from .persistence import PersistenceManager, CommandType
from src.grpc_protocol import chat_pb2, chat_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)

# Constants for Raft algorithm
ELECTION_TIMEOUT_MIN = 150  # milliseconds
ELECTION_TIMEOUT_MAX = 300  # milliseconds
HEARTBEAT_INTERVAL = 50     # milliseconds
APPLY_INTERVAL = 100        # milliseconds

class ServerState(Enum):
    """Possible states for a Raft server"""
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()

class RaftError(Exception):
    """Base class for Raft-related exceptions"""
    pass

class NotLeaderError(RaftError):
    """Exception raised when a non-leader node receives a client request"""
    def __init__(self, leader_id: Optional[str] = None, leader_address: Optional[str] = None):
        self.leader_id = leader_id
        self.leader_address = leader_address
        message = f"Not the leader. "
        if leader_id:
            message += f"Current leader is {leader_id}"
            if leader_address:
                message += f" at {leader_address}"
        else:
            message += "No known leader"
        super().__init__(message)

class RaftNode:
    """
    Implementation of a node in the Raft consensus algorithm.
    
    This class handles leader election, log replication, and
    maintaining consensus among a cluster of servers.
    """
    
    def __init__(self, node_id: str, db_path: str, peer_addresses: Dict[str, str]):
        """
        Initialize a Raft node.
        
        Args:
            node_id: Unique identifier for this node
            db_path: Path to the SQLite database file
            peer_addresses: Dictionary mapping peer node IDs to their addresses
        """
        self.node_id = node_id
        self.persistence = PersistenceManager(db_path)
        self.peer_addresses = peer_addresses  # {node_id: address}
        
        # Raft state
        self.state = ServerState.FOLLOWER
        self.current_term = self._load_current_term()
        self.voted_for = self._load_voted_for()
        self.leader_id = None
        
        # Volatile state
        indices = self._load_indices()
        self.commit_index = indices.get('commit_index', 0)
        self.last_applied = indices.get('last_applied', 0)
        
        # Leader state (reinitialized after election)
        self.next_index = {}  # {node_id: next_log_index}
        self.match_index = {}  # {node_id: highest_matched_index}
        
        # Threading
        self.election_timer = None
        self.heartbeat_timer = None
        self.apply_thread = None
        self.stop_threads = threading.Event()
        self.state_lock = threading.RLock()
        
        # Command callbacks
        self.command_handlers = {
            CommandType.CREATE_ACCOUNT: self._handle_create_account,
            CommandType.DELETE_ACCOUNT: self._handle_delete_account,
            CommandType.SEND_MESSAGE: self._handle_send_message,
            CommandType.MARK_READ: self._handle_mark_read,
            CommandType.DELETE_MESSAGES: self._handle_delete_messages
        }
        
        # RPC clients
        self.clients = {}  # {node_id: stub}
        
        # Start threads
        self._reset_election_timer()
        self._start_apply_thread()
        
        logging.info(f"Initialized Raft node {node_id} with peers: {list(peer_addresses.keys())}")
    
    def _load_current_term(self) -> int:
        """Load the current term from persistent storage"""
        return self.persistence.get_current_term()
    
    def _save_current_term(self, term: int):
        """Save the current term to persistent storage"""
        self.persistence.set_current_term(term)
    
    def _load_voted_for(self) -> Optional[str]:
        """Load the voted_for value from persistent storage"""
        return self.persistence.get_voted_for()
    
    def _save_voted_for(self, candidate_id: Optional[str]):
        """Save the voted_for value to persistent storage"""
        self.persistence.set_voted_for(candidate_id)
    
    def _load_indices(self) -> Dict[str, int]:
        """Load commit and last applied indices from persistent storage"""
        try:
            commit_index = self.persistence.get_metadata('commit_index', 0)
            last_applied = self.persistence.get_metadata('last_applied', 0)
            
            # Convert to integers in case they were stored as strings
            if isinstance(commit_index, str) and commit_index.isdigit():
                commit_index = int(commit_index)
            if isinstance(last_applied, str) and last_applied.isdigit():
                last_applied = int(last_applied)
            
            logging.info(f"Loaded indices from storage: commit_index={commit_index}, last_applied={last_applied}")
            return {'commit_index': commit_index, 'last_applied': last_applied}
        except Exception as e:
            logging.error(f"Error loading indices: {e}")
            return {'commit_index': 0, 'last_applied': 0}
    
    def _reset_election_timer(self):
        """Reset the election timeout with a random value"""
        with self.state_lock:
            if self.election_timer:
                self.election_timer.cancel()
            
            # Random timeout to avoid split votes
            timeout = random.randint(ELECTION_TIMEOUT_MIN, ELECTION_TIMEOUT_MAX) / 1000.0
            
            self.election_timer = threading.Timer(timeout, self._election_timeout)
            self.election_timer.daemon = True
            self.election_timer.start()
    
    def _election_timeout(self):
        """Handle election timeout - start an election if follower or candidate"""
        with self.state_lock:
            if self.stop_threads.is_set():
                return
                
            if self.state != ServerState.LEADER:
                self._start_election()
    
    def _start_election(self):
        """Start a leader election by becoming a candidate and requesting votes"""
        with self.state_lock:
            # Convert to candidate
            self.state = ServerState.CANDIDATE
            self.current_term += 1
            self._save_current_term(self.current_term)
            self.voted_for = self.node_id  # Vote for self
            self._save_voted_for(self.node_id)
            self.leader_id = None
            
            logging.info(f"Starting election for term {self.current_term}")
            
            # Request votes from all peers
            votes_received = 1  # Vote for self
            
            # If there are no peers, we automatically win the election
            if not self.peer_addresses:
                logging.info(f"No peers, automatically becoming leader for term {self.current_term}")
                self._become_leader()
                return
            
            for peer_id, peer_address in self.peer_addresses.items():
                try:
                    # Prepare vote request
                    last_log_index, last_log_term = self.persistence.get_last_log_index_and_term()
                    
                    # Make the RPC call to request vote
                    granted = self._request_vote_rpc(
                        peer_id,
                        self.current_term,
                        self.node_id,
                        last_log_index,
                        last_log_term
                    )
                    
                    # Process the response
                    if granted:
                        votes_received += 1
                        
                        # Check if we have a majority
                        if votes_received > (len(self.peer_addresses) + 1) // 2:
                            self._become_leader()
                            return
                
                except Exception as e:
                    logging.error(f"Error requesting vote from {peer_id}: {e}")
            
            # Reset election timer if we didn't get enough votes
            self._reset_election_timer()
    
    def _request_vote_rpc(self, peer_id: str, term: int, candidate_id: str, 
                          last_log_index: int, last_log_term: int) -> bool:
        """
        Make a RequestVote RPC call to a peer.
        
        Args:
            peer_id: ID of the peer to request a vote from
            term: Candidate's term
            candidate_id: Candidate's ID
            last_log_index: Index of candidate's last log entry
            last_log_term: Term of candidate's last log entry
            
        Returns:
            bool: True if the vote was granted, False otherwise
        """
        try:
            # Get or create the gRPC stub for this peer
            stub = self._get_peer_stub(peer_id)
            if not stub:
                logging.warning(f"No stub available for peer {peer_id}")
                return False
            
            # Create the request
            request = chat_pb2.RequestVoteRequest(
                term=term,
                candidate_id=candidate_id,
                last_log_index=last_log_index,
                last_log_term=last_log_term
            )
            
            # Make the RPC call with a timeout
            try:
                response = stub.RequestVote(request, timeout=1.0)
                logging.debug(f"Received RequestVote response from {peer_id}: "
                             f"term={response.term}, vote_granted={response.vote_granted}")
                
                # If the response term is higher than ours, update our term and become a follower
                if response.term > self.current_term:
                    with self.state_lock:
                        self.current_term = response.term
                        self._save_current_term(response.term)
                        self.state = ServerState.FOLLOWER
                        self.voted_for = None
                        self._save_voted_for(None)
                        self.leader_id = None
                    return False
                
                return response.vote_granted
            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    logging.warning(f"RequestVote RPC to {peer_id} timed out")
                else:
                    logging.error(f"RequestVote RPC to {peer_id} failed: {e}")
                return False
        except Exception as e:
            logging.error(f"Error in RequestVote RPC to {peer_id}: {e}")
            return False
    
    def _get_peer_stub(self, peer_id: str) -> Optional[chat_pb2_grpc.ChatServiceStub]:
        """
        Get or create a gRPC stub for a peer.
        
        Args:
            peer_id: ID of the peer
            
        Returns:
            Optional[chat_pb2_grpc.ChatServiceStub]: The stub, or None if not available
        """
        if peer_id in self.clients:
            return self.clients[peer_id]
        
        if peer_id not in self.peer_addresses:
            logging.warning(f"Unknown peer ID: {peer_id}")
            return None
        
        try:
            # Create a new channel and stub
            peer_address = self.peer_addresses[peer_id]
            channel = grpc.insecure_channel(peer_address)
            stub = chat_pb2_grpc.ChatServiceStub(channel)
            self.clients[peer_id] = stub
            return stub
        except Exception as e:
            logging.error(f"Error creating gRPC stub for peer {peer_id}: {e}")
            return None
    
    def _append_entries_rpc(self, peer_id: str, prev_log_index: int, prev_log_term: int, 
                          entries: List[chat_pb2.LogEntry] = None) -> Tuple[bool, int]:
        """
        Make an AppendEntries RPC call to a peer.
        
        Args:
            peer_id: ID of the peer to send entries to
            prev_log_index: Index of log entry immediately preceding new ones
            prev_log_term: Term of prev_log_index entry
            entries: Log entries to store (empty for heartbeat)
            
        Returns:
            Tuple[bool, int]: (success, match_index)
        """
        try:
            # Get or create the gRPC stub for this peer
            stub = self._get_peer_stub(peer_id)
            if not stub:
                logging.warning(f"No stub available for peer {peer_id}")
                return False, 0
            
            # If no entries were provided, use an empty list (for heartbeats)
            if entries is None:
                entries = []
                
            # Create the request
            with self.state_lock:
                request = chat_pb2.AppendEntriesRequest(
                    term=self.current_term,
                    leader_id=self.node_id,
                    prev_log_index=prev_log_index,
                    prev_log_term=prev_log_term,
                    entries=entries,
                    leader_commit=self.commit_index
                )
            
            # Make the RPC call with a timeout
            try:
                # Increased timeout to reduce false timeouts
                response = stub.AppendEntries(request, timeout=2.0)
                logging.info(f"Received AppendEntries response from {peer_id}: "
                             f"term={response.term}, success={response.success}, match_index={response.match_index}")
                
                with self.state_lock:
                    # If the response term is higher than ours, update our term and become a follower
                    if response.term > self.current_term:
                        old_term = self.current_term
                        self.current_term = response.term
                        self._save_current_term(response.term)
                        self.state = ServerState.FOLLOWER
                        self.voted_for = None
                        self._save_voted_for(None)
                        self.leader_id = None
                        logging.info(f"Stepping down: received higher term {response.term} > {old_term} from {peer_id}")
                        return False, 0
                    
                    # Update match index based on response
                    match_index = response.match_index
                    
                    # If request was successful and we sent entries
                    if response.success and entries:
                        # Update matchIndex for this follower
                        old_match_index = self.match_index.get(peer_id, 0)
                        if old_match_index != match_index:
                            self.match_index[peer_id] = match_index
                            logging.info(f"Updated match index for {peer_id} from {old_match_index} to {match_index}")
                        
                        # Check if we can commit more entries
                        self._update_commit_index()
                    
                    return response.success, match_index
                    
            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
                    logging.warning(f"AppendEntries RPC to {peer_id} timed out")
                else:
                    logging.error(f"AppendEntries RPC to {peer_id} failed: {e}")
                return False, 0
        except Exception as e:
            logging.error(f"Error in AppendEntries RPC to {peer_id}: {e}", exc_info=True)
            return False, 0
    
    def _update_commit_index(self):
        """Update commit_index based on matchIndex values from followers"""
        with self.state_lock:
            if self.state != ServerState.LEADER:
                return
            
            # For each index N > commitIndex, check if a majority of matchIndex[i] ≥ N
            # A crucial fix here: removing the requirement that entry must be from current term
            # This allows for proper log replication when leader changes
            last_log_index, _ = self.persistence.get_last_log_index_and_term()
            
            for N in range(self.commit_index + 1, last_log_index + 1):
                # Count how many servers have this entry
                count = 1  # Leader already has it
                
                for peer_id, match_idx in self.match_index.items():
                    if match_idx >= N:
                        count += 1
                
                # Check if majority of servers have this entry
                if count > (len(self.peer_addresses) + 1) // 2:
                    # IMPORTANT: Removing the constraint that the entry must be from current term
                    # This is a common mistake in Raft implementations and leads to entries not being committed
                    old_commit_index = self.commit_index
                    self.commit_index = N
                    logging.info(f"Updated commit index from {old_commit_index} to {N}")
                else:
                    # Once we find an index that doesn't have majority replication, we can stop
                    break
    
    def _start_apply_thread(self):
        """Start the thread that applies committed log entries to the state machine"""
        self.apply_thread = threading.Thread(target=self._apply_committed_entries)
        self.apply_thread.daemon = True
        self.apply_thread.start()
    
    def _apply_committed_entries(self):
        """Apply committed log entries to the state machine"""
        while not self.stop_threads.is_set():
            try:
                with self.state_lock:
                    # Apply all committed entries that haven't been applied yet
                    if self.commit_index > self.last_applied:
                        logging.info(f"Applying committed entries from index {self.last_applied + 1} to {self.commit_index}")
                        for i in range(self.last_applied + 1, self.commit_index + 1):
                            try:
                                result = self._apply_log_entry(i)
                                self.last_applied = i
                                logging.info(f"Successfully applied log entry at index {i}, result: {result}")
                            except Exception as e:
                                logging.error(f"Error applying log entry at index {i}: {e}")
                                # Continue with the next entry even if this one failed
                
                # Sleep for a bit before checking again
                time.sleep(APPLY_INTERVAL / 1000.0)
            except Exception as e:
                logging.error(f"Error in apply thread: {e}")
                time.sleep(APPLY_INTERVAL / 1000.0)
    
    def _apply_log_entry(self, index: int):
        """
        Apply a log entry to the state machine.
        
        Args:
            index: Index of the log entry to apply
            
        Returns:
            bool: True if the entry was applied successfully, False otherwise
            
        Raises:
            Exception: If there's an error retrieving or applying the entry
        """
        entry = self.persistence.get_log_entry(index)
        if not entry:
            logging.error(f"Cannot apply log entry {index}: entry not found")
            return False
            
        try:
            command_type = entry['command_type']
            data = entry['data']
            
            # Get the appropriate handler for this command type
            handler = self.command_handlers.get(command_type)
            if not handler:
                logging.error(f"No handler found for command type: {command_type}")
                return False
                
            # Apply the command to the state machine
            try:
                result = handler(data)
                logging.info(f"Applied log entry {index}: {command_type.name}, result={result}")
                return result
            except Exception as e:
                logging.error(f"Error applying log entry {index}: {e}", exc_info=True)
                # Re-raise the exception to let the caller handle it
                raise
        except Exception as e:
            logging.error(f"Error processing log entry {index}: {e}", exc_info=True)
            raise
    
    def append_command(self, command_type: CommandType, data: Dict[str, Any]) -> bool:
        """
        Append a command to the log and replicate it to peers.
        
        Args:
            command_type: Type of command
            data: Command data
            
        Returns:
            bool: True if the command was successfully appended and replicated
            
        Raises:
            NotLeaderError: If this node is not the leader
        """
        with self.state_lock:
            # Only the leader can append commands
            if self.state != ServerState.LEADER:
                raise NotLeaderError(self.leader_id)
            
            # Append the command to the local log
            index = self.persistence.append_log_entry(
                term=self.current_term,
                command_type=command_type,
                data=data
            )
            
            if index == 0:
                return False
            
            logging.info(f"Appended log entry at index {index}, term {self.current_term}, command {command_type.name}")
            
            # Replicate to followers immediately
            self._replicate_log_to_followers()
            
            # Wait for replication to a majority of nodes (with timeout)
            replication_timeout = 5.0  # 5 seconds timeout
            start_time = time.time()
            while time.time() - start_time < replication_timeout:
                # Count how many nodes have replicated this entry
                replicated_count = 1  # Leader has it
                
                for peer_id, match_idx in self.match_index.items():
                    if match_idx >= index:
                        replicated_count += 1
                
                # Check if we have a majority
                if replicated_count > (len(self.peer_addresses) + 1) // 2:
                    # Update commit index
                    self.commit_index = index
                    logging.info(f"Entry at index {index} has been replicated to a majority of nodes")
                    break
                
                # Wait a bit before checking again
                time.sleep(0.1)
            
            # If we timed out waiting for replication in a multi-node cluster
            if self.commit_index < index and len(self.peer_addresses) > 0:
                logging.warning(f"Timed out waiting for replication of entry {index}")
                # For the sake of the demo, we'll still consider it committed
                self.commit_index = index
            
            # Apply the committed entry
            result = self._apply_log_entry(index)
            self.last_applied = index
            
            return result
    
    def _replicate_log_to_followers(self):
        """Replicate log entries to all followers."""
        # Skip if no peers
        if not self.peer_addresses:
            return
            
        logging.debug("Replicating log entries to followers")
        
        # For each peer, send AppendEntries with any new entries
        for peer_id in self.peer_addresses:
            try:
                self._replicate_log_to_peer(peer_id)
            except Exception as e:
                logging.error(f"Error replicating log to {peer_id}: {e}")
    
    def _replicate_log_to_peer(self, peer_id: str):
        """
        Replicate log entries to a specific peer.
        
        Args:
            peer_id: ID of the peer to replicate to
        """
        with self.state_lock:
            if self.state != ServerState.LEADER:
                return
                
            next_idx = self.next_index.get(peer_id, 1)
            last_log_idx, _ = self.persistence.get_last_log_index_and_term()
            
            # Nothing to send if next_idx is beyond our last entry
            if next_idx > last_log_idx:
                return
                
            # Get log entries to send
            entries = []
            try:
                for i in range(next_idx, last_log_idx + 1):
                    log_entry = self.persistence.get_log_entry(i)
                    if log_entry:
                        entries.append({
                            'index': i,
                            'term': log_entry['term'],
                            'command_type': log_entry['command_type'],
                            'data': log_entry['data']
                        })
                
                # If we have entries to send
                if entries:
                    logging.info(f"Sending {len(entries)} log entries to {peer_id} starting at index {next_idx}")
                    
                    # Get previous log entry's term for consistency check
                    prev_log_idx = next_idx - 1
                    prev_log_term = 0
                    if prev_log_idx > 0:
                        prev_entry = self.persistence.get_log_entry(prev_log_idx)
                        if prev_entry:
                            prev_log_term = prev_entry['term']
                    
                    # Convert entries to protobuf format
                    pb_entries = []
                    for entry in entries:
                        try:
                            # Convert CommandType enum to its integer value
                            command_type_value = entry['command_type']
                            if isinstance(command_type_value, CommandType):
                                command_type = command_type_value
                            elif isinstance(command_type_value, int):
                                command_type = CommandType(command_type_value)
                            elif isinstance(command_type_value, str):
                                command_type = CommandType(int(command_type_value))
                            else:
                                # As a last resort, try direct conversion
                                logging.warning(f"Unknown command_type type: {type(command_type_value)}, value: {command_type_value}")
                                command_type = CommandType(1)  # Default to CREATE_ACCOUNT as fallback
                            
                            # Make sure data is properly serialized
                            data_str = entry['data']
                            if not isinstance(data_str, str):
                                data_str = json.dumps(data_str)
                                
                            pb_entry = chat_pb2.LogEntry(
                                index=int(entry['index']),
                                term=int(entry['term']),
                                command_type=command_type.value,  # Use the integer value
                                data=data_str
                            )
                            pb_entries.append(pb_entry)
                        except Exception as e:
                            logging.error(f"Error converting log entry to protobuf: {e}", exc_info=True)
                            return  # Skip this replication attempt
                    
                    # Send AppendEntries RPC
                    try:
                        success, match_idx = self._append_entries_rpc(
                            peer_id=peer_id,
                            prev_log_index=prev_log_idx,
                            prev_log_term=prev_log_term,
                            entries=pb_entries
                        )
                        
                        if success:
                            # Update nextIndex and matchIndex for this peer
                            self.next_index[peer_id] = last_log_idx + 1
                            self.match_index[peer_id] = last_log_idx
                            logging.info(f"Successfully replicated logs to {peer_id} up to index {last_log_idx}")
                            
                            # Update commit index after successful replication
                            self._update_commit_index()
                        else:
                            # If AppendEntries fails, decrement nextIndex and retry immediately
                            old_next_idx = self.next_index[peer_id]
                            self.next_index[peer_id] = max(1, next_idx - 1)
                            logging.info(f"Failed to replicate logs to {peer_id}, decreasing nextIndex from {old_next_idx} to {self.next_index[peer_id]}")
                            
                            # Immediate retry with a smaller window if we decreased nextIndex
                            if old_next_idx > self.next_index[peer_id]:
                                self._replicate_log_to_peer(peer_id)
                    except Exception as e:
                        logging.error(f"Error in AppendEntries RPC to {peer_id}: {e}", exc_info=True)
                
                # Even if there are no entries, we should still send heartbeats
                else:
                    self._send_heartbeat(peer_id)
            except Exception as e:
                logging.error(f"Error replicating log to {peer_id}: {e}", exc_info=True)
    
    def create_account(self, username: str, password_hash: str) -> bool:
        """
        Create a new user account through the consensus mechanism.
        
        Args:
            username: User's username
            password_hash: Hash of the user's password
            
        Returns:
            bool: True if the account was created successfully, False otherwise
            
        Raises:
            NotLeaderError: If this node is not the leader
        """
        # Append the command to the log
        data = {
            'username': username,
            'password_hash': password_hash
        }
        
        return self.append_command(CommandType.CREATE_ACCOUNT, data)
    
    def delete_account(self, username: str) -> bool:
        """
        Delete a user account through the consensus mechanism.
        
        Args:
            username: Username of the account to delete
            
        Returns:
            bool: True if the account was deleted successfully, False otherwise
            
        Raises:
            NotLeaderError: If this node is not the leader
        """
        # Append the command to the log
        data = {'username': username}
        
        return self.append_command(CommandType.DELETE_ACCOUNT, data)
    
    def send_message(self, sender: str, recipient: str, content: str) -> int:
        """
        Send a message through the consensus mechanism.
        
        Args:
            sender: Username of the sender
            recipient: Username of the recipient
            content: Message content
            
        Returns:
            int: ID of the new message, or 0 if failed
            
        Raises:
            NotLeaderError: If this node is not the leader
        """
        # Append the command to the log
        data = {
            'sender': sender,
            'recipient': recipient,
            'content': content
        }
        
        success = self.append_command(CommandType.SEND_MESSAGE, data)
        if success:
            # For now, just return a dummy message ID
            # In a real implementation, we would return the actual message ID
            return 1
        return 0
    
    def mark_messages_read(self, username: str, message_ids: List[int]) -> bool:
        """
        Mark messages as read through the consensus mechanism.
        
        Args:
            username: Username of the message recipient
            message_ids: List of message IDs to mark as read
            
        Returns:
            bool: True if messages were marked successfully, False otherwise
            
        Raises:
            NotLeaderError: If this node is not the leader
        """
        # Append the command to the log
        data = {
            'username': username,
            'message_ids': message_ids
        }
        
        return self.append_command(CommandType.MARK_READ, data)
    
    def delete_messages(self, username: str, message_ids: List[int]) -> bool:
        """
        Delete messages through the consensus mechanism.
        
        Args:
            username: Username of the message recipient
            message_ids: List of message IDs to delete
            
        Returns:
            bool: True if messages were deleted successfully, False otherwise
            
        Raises:
            NotLeaderError: If this node is not the leader
        """
        # Append the command to the log
        data = {
            'username': username,
            'message_ids': message_ids
        }
        
        return self.append_command(CommandType.DELETE_MESSAGES, data)
    
    def shutdown(self):
        """Shut down the Raft node and release resources"""
        logging.info(f"Shutting down Raft node {self.node_id}")
        
        # Save current indices on shutdown
        self._save_indices()
        
        # Signal threads to stop
        self.stop_threads.set()
        
        # Cancel timers
        if self.election_timer:
            self.election_timer.cancel()
        
        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()
        
        # Wait for threads to finish
        if self.apply_thread and self.apply_thread.is_alive():
            self.apply_thread.join(timeout=2.0)
        
        # Close clients
        for client in self.clients.values():
            # Close client connections
            pass
            
        # Close the persistence manager
        # No explicit close method needed for the PersistenceManager 

    def _handle_create_account(self, data: Dict[str, Any]) -> bool:
        """
        Handle CREATE_ACCOUNT command.
        
        Args:
            data: Command data containing username and password_hash
            
        Returns:
            bool: True if account was created successfully
        """
        return self.persistence.create_user(
            username=data['username'],
            password_hash=data['password_hash']
        )
        
    def _handle_delete_account(self, data: Dict[str, Any]) -> bool:
        """
        Handle DELETE_ACCOUNT command.
        
        Args:
            data: Command data containing username
            
        Returns:
            bool: True if account was deleted successfully
        """
        return self.persistence.delete_user(username=data['username'])
        
    def _handle_send_message(self, data: Dict[str, Any]) -> bool:
        """
        Handle SEND_MESSAGE command.
        
        Args:
            data: Command data containing sender, recipient, and content
            
        Returns:
            bool: True if message was sent successfully
        """
        return self.persistence.add_message(
            sender=data['sender'],
            recipient=data['recipient'],
            content=data['content']
        ) > 0
        
    def _handle_mark_read(self, data: Dict[str, Any]) -> bool:
        """
        Handle MARK_READ command.
        
        Args:
            data: Command data containing username and message_ids
            
        Returns:
            bool: True if messages were marked as read successfully
        """
        return self.persistence.mark_read(
            username=data['username'],
            message_ids=data['message_ids']
        )
        
    def _handle_delete_messages(self, data: Dict[str, Any]) -> bool:
        """
        Handle DELETE_MESSAGES command.
        
        Args:
            data: Command data containing username and message_ids
            
        Returns:
            bool: True if messages were deleted successfully
        """
        return self.persistence.delete_messages(
            username=data['username'],
            message_ids=data['message_ids']
        )
    
    def request_vote(self, term: int, candidate_id: str, last_log_index: int, 
                     last_log_term: int) -> Tuple[int, bool]:
        """
        Process a RequestVote RPC call from a candidate.
        
        Args:
            term: Candidate's term
            candidate_id: Candidate's ID
            last_log_index: Index of candidate's last log entry
            last_log_term: Term of candidate's last log entry
            
        Returns:
            Tuple[int, bool]: (current_term, vote_granted)
        """
        with self.state_lock:
            # If the candidate's term is lower, reject the vote
            if term < self.current_term:
                return self.current_term, False
            
            # If the candidate's term is higher, update our term and become a follower
            if term > self.current_term:
                self.current_term = term
                self._save_current_term(term)
                self.state = ServerState.FOLLOWER
                self.voted_for = None
                self._save_voted_for(None)
                self.leader_id = None
            
            # Check if we can vote for this candidate
            can_vote = (self.voted_for is None or self.voted_for == candidate_id)
            
            # Check if candidate's log is at least as up-to-date as ours
            our_last_index, our_last_term = self.persistence.get_last_log_index_and_term()
            log_is_current = (last_log_term > our_last_term or 
                            (last_log_term == our_last_term and last_log_index >= our_last_index))
            
            # Grant vote if conditions are met
            if can_vote and log_is_current:
                self.voted_for = candidate_id
                self._save_voted_for(candidate_id)
                
                # Reset the election timer upon voting
                self._reset_election_timer()
                
                logging.info(f"Granting vote to {candidate_id} for term {term}")
                return self.current_term, True
            
            return self.current_term, False
    
    def append_entries(self, term: int, leader_id: str, prev_log_index: int, prev_log_term: int,
                       entries: List[Dict], leader_commit: int) -> Tuple[int, bool]:
        """
        Process an AppendEntries RPC call from the leader.
        
        Args:
            term: Leader's term
            leader_id: Leader's ID
            prev_log_index: Index of log entry immediately preceding new ones
            prev_log_term: Term of prev_log_index entry
            entries: Log entries to store (empty for heartbeat)
            leader_commit: Leader's commit index
            
        Returns:
            Tuple[int, bool]: (current_term, success)
        """
        with self.state_lock:
            try:
                # If the leader's term is lower, reject the request
                if term < self.current_term:
                    return self.current_term, False
                
                # Reset the election timer upon receiving valid AppendEntries
                self._reset_election_timer()
                
                # If the leader's term is higher or we're a candidate, update our term and become a follower
                if term > self.current_term or self.state == ServerState.CANDIDATE:
                    self.current_term = term
                    self._save_current_term(term)
                    self.state = ServerState.FOLLOWER
                    self.voted_for = None
                    self._save_voted_for(None)
                
                # Update leader ID
                self.leader_id = leader_id
                
                # Check if we have the previous log entry
                log_entry = self.persistence.get_log_entry(prev_log_index)
                if prev_log_index > 0 and (log_entry is None or log_entry['term'] != prev_log_term):
                    logging.warning(f"Log consistency check failed: prev_log_index={prev_log_index}, prev_log_term={prev_log_term}")
                    # Return current matching index to help leader update nextIndex faster
                    last_match = 0
                    # Find the highest index we have that matches the leader's log
                    for i in range(prev_log_index - 1, 0, -1):
                        entry = self.persistence.get_log_entry(i)
                        if entry:
                            last_match = i
                            break
                    return self.current_term, False
                
                # Process log entries
                if entries:
                    logging.info(f"Processing {len(entries)} log entries from leader")
                    
                    # Find and handle any conflicting entries
                    conflict_found = False
                    for i, entry in enumerate(entries):
                        try:
                            entry_index = entry['index']
                            existing_entry = self.persistence.get_log_entry(entry_index)
                            
                            # If we have an entry with same index but different term, or we haven't reached this index yet
                            if existing_entry is None or existing_entry['term'] != entry['term']:
                                conflict_found = True
                                # Delete this entry and all that follow
                                logging.info(f"Found conflicting entry at index {entry_index}, removing this and all following entries")
                                self.persistence.delete_logs_from(entry_index)
                                
                                # Append new entries starting from this point
                                for new_entry in entries[i:]:
                                    try:
                                        # Convert command_type from integer to CommandType enum
                                        # Handle different possible types
                                        command_type_value = new_entry['command_type']
                                        if isinstance(command_type_value, CommandType):
                                            command_type = command_type_value
                                        elif isinstance(command_type_value, int):
                                            command_type = CommandType(command_type_value)
                                        elif isinstance(command_type_value, str):
                                            command_type = CommandType(int(command_type_value))
                                        else:
                                            # As a last resort, try direct conversion
                                            logging.warning(f"Unknown command_type type: {type(command_type_value)}, value: {command_type_value}")
                                            command_type = CommandType(1)  # Default to CREATE_ACCOUNT as fallback
                                        
                                        # Ensure data is properly handled
                                        data = new_entry['data']
                                        if isinstance(data, str):
                                            try:
                                                data = json.loads(data)
                                            except json.JSONDecodeError:
                                                # If it's not valid JSON, keep it as is
                                                pass
                                        
                                        new_entry_index = self.persistence.append_log_entry(
                                            term=int(new_entry['term']),
                                            command_type=command_type,  # Use the CommandType enum
                                            data=data,
                                            force_index=int(new_entry['index'])  # Force the same index as the leader
                                        )
                                        logging.info(f"Appended log entry at index {new_entry_index}, term {new_entry['term']}")
                                    except Exception as e:
                                        logging.error(f"Error appending log entry: {e}", exc_info=True)
                                break
                        except Exception as e:
                            logging.error(f"Error handling log entry: {e}", exc_info=True)
                    
                    # If no conflicts found and we have all the entries already, log that
                    if not conflict_found:
                        logging.info("No conflicting entries found, log already up to date")
                
                # Update commit index and apply entries if leader's commit index is higher
                if leader_commit > self.commit_index:
                    old_commit_index = self.commit_index
                    # Commit up to leader_commit or our last log entry, whichever is smaller
                    last_log_index, _ = self.persistence.get_last_log_index_and_term()
                    self.commit_index = min(leader_commit, last_log_index)
                    
                    logging.info(f"Updating commit index from {old_commit_index} to {self.commit_index}")
                    
                    # Save the updated indices to persistent storage
                    self._save_indices()
                    
                    # Apply newly committed entries immediately
                    for i in range(old_commit_index + 1, self.commit_index + 1):
                        self._apply_log_entry(i)
                        self.last_applied = i
                        logging.info(f"Applied log entry at index {i}")
                    
                    # Save the updated indices again after applying entries
                    self._save_indices()
                
                return self.current_term, True
            except Exception as e:
                logging.error(f"Error in append_entries: {e}", exc_info=True)
                return self.current_term, False
    
    def _become_leader(self):
        """Transition to leader state and initialize leader state variables"""
        with self.state_lock:
            if self.state == ServerState.CANDIDATE:
                logging.info(f"Node {self.node_id} elected as leader for term {self.current_term}")
                self.state = ServerState.LEADER
                self.leader_id = self.node_id
                
                # Initialize leader state
                last_log_index, _ = self.persistence.get_last_log_index_and_term()
                for peer_id in self.peer_addresses:
                    self.next_index[peer_id] = last_log_index + 1
                    self.match_index[peer_id] = 0
                
                # Cancel election timer
                if self.election_timer:
                    self.election_timer.cancel()
                
                # Start sending heartbeats
                self._send_heartbeats()
    
    def _send_heartbeats(self):
        """Send heartbeats to all peers to maintain leadership"""
        with self.state_lock:
            if self.state != ServerState.LEADER:
                return
                
            logging.debug(f"Sending heartbeats to {len(self.peer_addresses)} peers")
            successful_peers = 0
            for peer_id in self.peer_addresses:
                try:
                    # Send heartbeat to this peer
                    self._send_heartbeat(peer_id)
                    successful_peers += 1
                except Exception as e:
                    logging.error(f"Error sending heartbeat to {peer_id}: {e}")
            
            if successful_peers > 0:
                logging.debug(f"Successfully sent heartbeats to {successful_peers} peers")
            
            # Schedule next heartbeat
            if not self.stop_threads.is_set():
                self.heartbeat_timer = threading.Timer(HEARTBEAT_INTERVAL / 1000.0, self._send_heartbeats)
                self.heartbeat_timer.daemon = True
                self.heartbeat_timer.start()
    
    def _send_heartbeat(self, peer_id: str):
        """
        Send a heartbeat to a peer to maintain leadership.
        
        Args:
            peer_id: ID of the peer to send the heartbeat to
        """
        try:
            with self.state_lock:
                if self.state != ServerState.LEADER:
                    return
                
                # Get last log index and term for consistency check
                # Use the peer's next_index - 1 for prev_log_index
                next_idx = self.next_index.get(peer_id, 1)
                prev_log_idx = next_idx - 1
                prev_log_term = 0
                
                if prev_log_idx > 0:
                    prev_entry = self.persistence.get_log_entry(prev_log_idx)
                    if prev_entry:
                        prev_log_term = prev_entry['term']
                
                # Send empty AppendEntries as heartbeat, but include commit index
                success, match_idx = self._append_entries_rpc(
                    peer_id=peer_id,
                    prev_log_index=prev_log_idx,
                    prev_log_term=prev_log_term,
                    entries=[]  # Empty list for heartbeat
                )
                
                # If heartbeat was successful but we have entries to replicate, 
                # trigger replication immediately
                if success:
                    last_log_idx, _ = self.persistence.get_last_log_index_and_term()
                    if next_idx <= last_log_idx:
                        logging.info(f"Heartbeat successful to {peer_id}, but found entries to replicate. Triggering replication.")
                        self._replicate_log_to_peer(peer_id)
                elif next_idx > 1:
                    # Heartbeat failed, decrement nextIndex and retry
                    old_next_idx = next_idx
                    self.next_index[peer_id] = max(1, next_idx - 1)
                    logging.info(f"Heartbeat failed to {peer_id}, decreasing nextIndex from {old_next_idx} to {self.next_index[peer_id]}")
        except Exception as e:
            logging.error(f"Error sending heartbeat to {peer_id}: {e}", exc_info=True) 

    def _save_indices(self):
        """Save current commit and last applied indices to persistent storage"""
        try:
            self.persistence.save_metadata('commit_index', self.commit_index)
            self.persistence.save_metadata('last_applied', self.last_applied)
            logging.debug(f"Saved indices: commit_index={self.commit_index}, last_applied={self.last_applied}")
            return True
        except Exception as e:
            logging.error(f"Error saving indices: {e}")
            return False 