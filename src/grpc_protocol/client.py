"""
gRPC Chat Client Implementation

This module implements the client-side handling of the gRPC chat protocol.
It provides a high-level API for interacting with the chat server.
"""

import grpc
import logging
import time
import random
from typing import List, Dict, Optional, Union, Any, Tuple

from . import chat_pb2
from . import chat_pb2_grpc

class GRPCChatClient:
    """
    Client for the gRPC Chat service.
    
    This class provides a high-level API for connecting to a gRPC chat server
    and performing operations such as user authentication, sending messages,
    and retrieving messages.
    
    Attributes:
        servers: List of server addresses to connect to
        current_server_idx: Index of the current server in the servers list
        leader_address: Address of the current leader server (if known)
        channel: gRPC channel object
        stub: gRPC stub for making RPC calls
        username: Current authenticated username
        auth_status: Current authentication status
    """
    
    def __init__(self, server: str):
        """
        Initialize the gRPC chat client.
        
        Args:
            server: The server address in the format 'host:port',
                   or a comma-separated list of server addresses
        """
        # Parse server string
        options = ["10.250.231.222:9001", "10.250.231.222:9002", "10.250.121.174:9003"]
        random.shuffle(options)
        
        if server:
            self.servers = [server] + [option for option in options if option != server]
        else:
            self.servers = options            
            
        self.current_server_idx = 0
        self.leader_address = None
        
        # Create a mapping from node IDs to full addresses
        self.node_id_to_address = {
            "node1": "10.250.231.222:9001",
            "node2": "10.250.231.222:9002", 
            "node3": "10.250.121.174:9003"
        }
        
        self.channel = None
        self.stub = None
        
        self.username = None
        self.auth_status = False
        
        # Connect to the first server
        self.connect()
        
    def connect(self) -> bool:
        """
        Connect to a chat server.
        
        Tries to connect to any available server in the server list.
        
        Returns:
            bool: True if connected successfully, False otherwise
        """
        # Close existing channel if any
        if self.channel:
            self.channel.close()
            self.channel = None
            self.stub = None
        
        # Try all servers in the list
        servers_to_try = list(self.servers)  # Make a copy of the servers list
        
        # Try each server until one works
        for server in servers_to_try:
            logging.info(f"Attempting to connect to server: {server}")
            if self._connect_to(server):
                return True
        
        logging.error("Failed to connect to any server")
        return False
    
    def _connect_to(self, server_address: str) -> bool:
        """
        Connect to a specific server.
        
        Args:
            server_address: Server address in the format 'host:port'
            
        Returns:
            bool: True if connected successfully, False otherwise
        """
        try:
            logging.info(f"Connecting to server: {server_address}")
            
            # Close existing channel first
            if self.channel:
                self.channel.close()
            
            # Create new channel and stub
            self.channel = grpc.insecure_channel(server_address)
            self.stub = chat_pb2_grpc.ChatServiceStub(self.channel)
            
            # Test the connection with a simple RPC call with a short timeout
            try:
                response = self.stub.ListAccounts(
                    chat_pb2.ListAccountsRequest(pattern="*"), 
                    timeout=3.0
                )
                
                # If we get here, the connection was successful
                self.leader_address = server_address
                logging.info(f"Connected to server: {server_address}")
                return True
                
            except grpc.RpcError as e:
                if e.code() == grpc.StatusCode.FAILED_PRECONDITION and "leader" in e.details().lower():
                    # This is not the leader, but the connection works
                    logging.info(f"Connected to {server_address} but it's not the leader. Error: {e}")
                    # Try to extract leader info and redirect
                    if self._handle_rpc_error(e):
                        # Successfully redirected
                        return True
                    else:
                        # Couldn't redirect, but connection is valid
                        logging.warning(f"Couldn't redirect to leader, but connection is valid")
                        self.leader_address = None
                        return True
                else:
                    # Other RPC error
                    logging.warning(f"RPC error connecting to {server_address}: {e}")
                    self.stub = None
                    self.channel.close()
                    self.channel = None
                    return False
            
        except Exception as e:
            logging.warning(f"Failed to connect to server {server_address}: {e}")
            self.stub = None
            if self.channel:
                self.channel.close()
                self.channel = None
            return False
    
    def close(self):
        """Close the connection to the server."""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.stub = None
    
    def _handle_rpc_error(self, e: grpc.RpcError) -> bool:
        """
        Handle RPC errors, including leader redirection.
        
        Args:
            e: The RPC error to handle
            
        Returns:
            bool: True if the error was handled and the operation should be retried,
                 False if the error could not be handled
        """
        status_code = e.code()
        details = e.details()
        logging.info(f"Handling RPC error: {status_code}, details: {details}")
        
        if status_code == grpc.StatusCode.FAILED_PRECONDITION:
            # This server is not the leader, try to parse the error message
            # to find the leader address
            
            # Try different formats of leader information in the error
            leader_id = None
            
            # Format: "Not the leader. Try node2"
            if "Try " in details:
                leader_id = details.split("Try ")[1].strip()
                logging.info(f"Found leader_id in 'Try' format: {leader_id}")
            
            # Format: "Not the leader. Current leader is node2"
            elif "leader is " in details:
                leader_id = details.split("leader is ")[1].strip()
                logging.info(f"Found leader_id in 'leader is' format: {leader_id}")
            
            # Format: any string containing "nodeX"
            else:
                for server_id in ["node1", "node2", "node3", "node4", "node5"]:
                    if server_id in details:
                        leader_id = server_id
                        logging.info(f"Found leader_id by keyword matching: {leader_id}")
                        break
            
            if leader_id:
                # Try to map node ID to full address using our mapping
                if leader_id in self.node_id_to_address:
                    leader_address = self.node_id_to_address[leader_id]
                    logging.info(f"Mapped leader ID {leader_id} to address {leader_address}")
                    
                    # Connect to the leader
                    self.leader_address = leader_address
                    if self._connect_to(self.leader_address):
                        return True
                
                # Fall back to old method - look for server with node ID in address
                for server in self.servers:
                    if leader_id in server:
                        self.leader_address = server
                        logging.info(f"Redirecting to leader at {self.leader_address}")
                        if self._connect_to(self.leader_address):
                            return True
                
                # If we couldn't find the server by name, try them all again
                logging.info(f"Couldn't find server for leader_id {leader_id}, trying all servers")
                if self.connect():
                    return True
        
        elif status_code in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED]:
            # Server is unavailable, try to reconnect
            logging.warning(f"Server unavailable: {e}")
            if self.connect():
                return True
        
        return False
    
    def create_account(self, username: str, password_hash: str) -> Tuple[bool, str]:
        """
        Create a new user account.
        
        Args:
            username: Username for the new account
            password_hash: Hash of the user's password
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        logging.info(f"Attempting to create account for user: {username}")
        
        # Check if stub exists
        if self.stub is None:
            logging.error("Cannot create account: stub is None, attempting to reconnect")
            if not self.connect():
                return False, "Failed to connect to any server"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            logging.info(f"Create account attempt {retry_count + 1}/{max_retries}")
            try:
                request = chat_pb2.CreateAccountRequest(
                    username=username,
                    password_hash=password_hash
                )
                
                logging.info(f"Sending CreateAccount request to server at {self.leader_address or 'unknown'}")
                response = self.stub.CreateAccount(request, timeout=5.0)
                
                if response.success:
                    logging.info(f"Account successfully created for {username}")
                    return True, ""
                else:
                    logging.warning(f"Account creation failed: {response.error_message}")
                    return False, response.error_message
            
            except grpc.RpcError as e:
                logging.error(f"RPC error during account creation: {e.code()}, {e.details()}")
                if self._handle_rpc_error(e):
                    retry_count += 1
                    backoff_time = 0.5 * retry_count
                    logging.info(f"Retrying after {backoff_time} seconds (attempt {retry_count}/{max_retries})")
                    time.sleep(backoff_time)  # Exponential backoff
                else:
                    logging.error(f"Failed to handle RPC error: {e}")
                    return False, str(e)
            
            except Exception as e:
                logging.exception(f"Unexpected error during account creation: {e}")
                return False, str(e)
        
        logging.error("Account creation failed: Max retries exceeded")
        return False, "Max retries exceeded"
    
    def login(self, username: str, password_hash: str) -> Tuple[bool, str]:
        """
        Authenticate with the server.
        
        Args:
            username: Username to authenticate with
            password_hash: Hash of the user's password
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        logging.info(f"Attempting to log in as user: {username}")
        
        # Check if stub exists
        if self.stub is None:
            logging.error("Cannot log in: stub is None, attempting to reconnect")
            if not self.connect():
                return False, "Failed to connect to any server"
                
        max_retries = 3
        retry_count = 0
        
        # For authentication (read operation), try all nodes if needed
        all_servers = list(self.servers)  # Make a copy of server list
        
        while retry_count < max_retries:
            logging.info(f"Login attempt {retry_count + 1}/{max_retries}")
            try:
                request = chat_pb2.AuthRequest(
                    username=username,
                    password_hash=password_hash
                )
                
                logging.info(f"Sending Authentication request to server at {self.leader_address or 'unknown'}")
                response = self.stub.Authenticate(request, timeout=5.0)
                
                if response.success:
                    logging.info(f"Successfully logged in as {username}")
                    self.username = username
                    self.auth_status = True
                    return True, ""
                else:
                    # If this is a valid authentication failure (not a network/leader issue)
                    logging.warning(f"Login failed: {response.error_message}")
                    self.username = None
                    self.auth_status = False
                    return False, response.error_message
            
            except grpc.RpcError as e:
                logging.error(f"RPC error during login: {e.code()}, {e.details()}")
                
                # If this is a "not leader" error, try to handle it
                if e.code() == grpc.StatusCode.FAILED_PRECONDITION and "leader" in e.details().lower():
                    if self._handle_rpc_error(e):
                        retry_count += 1
                        backoff_time = 0.5 * retry_count
                        logging.info(f"Retrying after {backoff_time} seconds (attempt {retry_count}/{max_retries})")
                        time.sleep(backoff_time)  # Exponential backoff
                        continue
                
                # For authentication, try connecting to a different server directly if available
                if all_servers:
                    # Try a different server
                    next_server = all_servers.pop(0)
                    if next_server != self.leader_address:
                        logging.info(f"Trying authentication with alternate server: {next_server}")
                        if self._connect_to(next_server):
                            continue
                
                # If no more servers to try or connection failed
                logging.error(f"Failed to handle RPC error: {e}")
                return False, str(e)
            
            except Exception as e:
                logging.exception(f"Unexpected error during login: {e}")
                return False, str(e)
        
        logging.error("Login failed: Max retries exceeded")
        return False, "Max retries exceeded"
    
    def _get_auth_metadata(self) -> List[Tuple[str, str]]:
        """
        Get authentication metadata for gRPC calls.
        
        Returns:
            List[Tuple[str, str]]: Metadata list with username
        """
        return [('username', self.username)] if self.username else []
    
    def send_message(self, recipient: str, content: str) -> Tuple[int, str]:
        """
        Send a message to another user.
        
        Args:
            recipient: Username of the recipient
            content: Message content
            
        Returns:
            Tuple[int, str]: (message_id, error_message)
        """
        if not self.auth_status:
            return 0, "Not authenticated"
        
        # Check if stub exists
        if self.stub is None:
            logging.error("Cannot send message: stub is None, attempting to reconnect")
            if not self.connect():
                return 0, "Failed to connect to any server"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            logging.info(f"Send message attempt {retry_count + 1}/{max_retries}")
            try:
                request = chat_pb2.SendMessageRequest(
                    recipient=recipient,
                    content=content
                )
                
                logging.info(f"Sending message to server at {self.leader_address or 'unknown'}")
                response = self.stub.SendMessage(
                    request,
                    metadata=self._get_auth_metadata(),
                    timeout=5.0
                )
                
                if response.message_id > 0:
                    logging.info(f"Message successfully sent to {recipient}")
                    return response.message_id, ""
                else:
                    logging.warning(f"Message sending failed: {response.error_message}")
                    return 0, response.error_message
            
            except grpc.RpcError as e:
                logging.error(f"RPC error during message sending: {e.code()}, {e.details()}")
                if self._handle_rpc_error(e):
                    retry_count += 1
                    backoff_time = 0.5 * retry_count
                    logging.info(f"Retrying after {backoff_time} seconds (attempt {retry_count}/{max_retries})")
                    time.sleep(backoff_time)  # Exponential backoff
                else:
                    logging.error(f"Failed to handle RPC error: {e}")
                    return 0, str(e)
            
            except Exception as e:
                logging.exception(f"Unexpected error during message sending: {e}")
                return 0, str(e)
        
        logging.error("Message sending failed: Max retries exceeded")
        return 0, "Max retries exceeded"
    
    def get_messages(self, include_read=False) -> Tuple[List[Dict], str]:
        """
        Get messages for the authenticated user.
        
        Args:
            include_read: Whether to include messages that have been read
            
        Returns:
            Tuple[List[Dict], str]: (messages, error_message)
        """
        if not self.auth_status:
            return [], "Not authenticated"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                request = chat_pb2.GetMessagesRequest(
                    include_read=include_read
                )
                
                response = self.stub.GetMessages(
                    request,
                    metadata=self._get_auth_metadata()
                )
                
                messages = []
                for msg in response.messages:
                    messages.append({
                        'id': msg.id,
                        'sender': msg.sender,
                        'recipient': msg.recipient,
                        'content': msg.content,
                        'timestamp': msg.timestamp,
                        'is_read': msg.is_read
                    })
                
                return messages, ""
            
            except grpc.RpcError as e:
                logging.error(f"RPC error during message retrieval: {e.code()}, {e.details()}")
                if self._handle_rpc_error(e):
                    retry_count += 1
                    time.sleep(0.5 * retry_count)  # Exponential backoff
                else:
                    return [], str(e)
            
            except Exception as e:
                return [], str(e)
        
        return [], "Max retries exceeded"
    
    def mark_read(self, message_ids: List[int]) -> Tuple[bool, str]:
        """
        Mark messages as read.
        
        Args:
            message_ids: List of message IDs to mark as read
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        return True, ""
        # if not self.auth_status:
        #     return False, "Not authenticated"
        
        # if not message_ids:
        #     return True, ""
        
        # max_retries = 3
        # retry_count = 0
        
        # while retry_count < max_retries:
        #     try:
        #         request = chat_pb2.MarkReadRequest(
        #             message_ids=message_ids
        #         )
                
        #         response = self.stub.MarkRead(
        #             request,
        #             metadata=self._get_auth_metadata()
        #         )
                
        #         if response.success:
        #             return True, ""
        #         else:
        #             return False, response.error_message
            
        #     except grpc.RpcError as e:
        #         logging.error(f"RPC error during message marking: {e.code()}, {e.details()}")
        #         if self._handle_rpc_error(e):
        #             retry_count += 1
        #             time.sleep(0.5 * retry_count)  # Exponential backoff
        #         else:
        #             return False, str(e)
            
        #     except Exception as e:
        #         return False, str(e)
        
        # return False, "Max retries exceeded"
    
    def delete_messages(self, message_ids: List[int]) -> Tuple[bool, str]:
        """
        Delete messages.
        
        Args:
            message_ids: List of message IDs to delete
            
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        if not self.auth_status:
            return False, "Not authenticated"
        
        if not message_ids:
            return True, ""
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                request = chat_pb2.DeleteMessagesRequest(
                    message_ids=message_ids
                )
                
                response = self.stub.DeleteMessages(
                    request,
                    metadata=self._get_auth_metadata()
                )
                
                if response.success:
                    return True, ""
                else:
                    return False, response.error_message
            
            except grpc.RpcError as e:
                logging.error(f"RPC error during message deletion: {e.code()}, {e.details()}")
                if self._handle_rpc_error(e):
                    retry_count += 1
                    time.sleep(0.5 * retry_count)  # Exponential backoff
                else:
                    return False, str(e)
            
            except Exception as e:
                return False, str(e)
        
        return False, "Max retries exceeded"
    
    def list_accounts(self, pattern: str = "*") -> Tuple[List[str], str]:
        """
        List user accounts matching pattern.
        
        Args:
            pattern: Pattern to match against usernames
            
        Returns:
            Tuple[List[str], str]: (usernames, error_message)
        """
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                request = chat_pb2.ListAccountsRequest(
                    pattern=pattern
                )
                
                response = self.stub.ListAccounts(request)
                
                return list(response.usernames), ""
            
            except grpc.RpcError as e:
                logging.error(f"RPC error during account listing: {e.code()}, {e.details()}")
                if self._handle_rpc_error(e):
                    retry_count += 1
                    time.sleep(0.5 * retry_count)  # Exponential backoff
                else:
                    return [], str(e)
            
            except Exception as e:
                return [], str(e)
        
        return [], "Max retries exceeded"
    
    def delete_account(self) -> Tuple[bool, str]:
        """
        Delete the current user's account.
        
        Returns:
            Tuple[bool, str]: (success, error_message)
        """
        if not self.auth_status:
            return False, "Not authenticated"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                request = chat_pb2.DeleteAccountRequest(
                    username=self.username
                )
                
                response = self.stub.DeleteAccount(
                    request,
                    metadata=self._get_auth_metadata()
                )
                
                if response.success:
                    self.username = None
                    self.auth_status = False
                    return True, ""
                else:
                    return False, response.error_message
            
            except grpc.RpcError as e:
                logging.error(f"RPC error during account deletion: {e.code()}, {e.details()}")
                if self._handle_rpc_error(e):
                    retry_count += 1
                    time.sleep(0.5 * retry_count)  # Exponential backoff
                else:
                    return False, str(e)
            
            except Exception as e:
                return False, str(e)
        
        return False, "Max retries exceeded"
    
    def get_cluster_status(self) -> Tuple[Dict[str, Any], str]:
        """
        Get status of the chat server cluster.
        
        Returns:
            Tuple[Dict[str, Any], str]: (status_dict, error_message)
        """
        # Check if stub exists
        if self.stub is None:
            logging.error("Cannot get cluster status: stub is None, attempting to reconnect")
            if not self.connect():
                return {}, "Failed to connect to any server. Try specifying multiple servers with --server server1,server2,server3"
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                request = chat_pb2.ClusterStatusRequest()
                
                response = self.stub.GetClusterStatus(request)
                
                status = {
                    'node_id': response.node_id,
                    'state': response.state,
                    'current_term': response.current_term,
                    'leader_id': response.leader_id,
                    'commit_index': response.commit_index,
                    'last_applied': response.last_applied,
                    'peer_count': response.peer_count,
                    'log_count': response.log_count
                }
                
                # Store leader ID for future connections
                if response.leader_id and response.leader_id in self.node_id_to_address:
                    self.leader_address = self.node_id_to_address[response.leader_id]
                    logging.info(f"Updated leader address to {self.leader_address}")
                
                return status, ""
            
            except grpc.RpcError as e:
                logging.error(f"RPC error during cluster status retrieval: {e.code()}, {e.details()}")
                if self._handle_rpc_error(e):
                    retry_count += 1
                    time.sleep(0.5 * retry_count)  # Exponential backoff
                else:
                    # Try all servers again
                    if self.connect():
                        retry_count += 1
                        continue
                    else:
                        return {}, f"Server unavailable: {str(e)}. Try connecting to a different node."
            
            except Exception as e:
                return {}, str(e)
        
        return {}, "Max retries exceeded. Try connecting to a different node."
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the server node, including Raft state.
        
        Returns:
            Dict[str, Any]: Status information including state, term, leader, commit_index, etc.
        """
        logging.info(f"Getting status from server at {self.leader_address or 'unknown'}")
        
        # Check if stub exists
        if self.stub is None:
            logging.error("Cannot get status: stub is None, attempting to reconnect")
            if not self.connect():
                return {"error": "Failed to connect to any server"}
        
        try:
            request = chat_pb2.StatusRequest()
            response = self.stub.GetStatus(request, timeout=5.0)
            
            status = {
                "state": self._state_enum_to_string(response.state),
                "term": response.current_term,
                "leader_id": response.leader_id,
                "commit_index": response.commit_index,
                "last_applied": response.last_applied
            }
            
            logging.info(f"Got status: {status}")
            return status
            
        except grpc.RpcError as e:
            logging.error(f"RPC error getting status: {e.code()}, {e.details()}")
            
            if self._handle_rpc_error(e):
                # Try again with the new connection
                return self.get_status()
            
            return {"error": str(e)}
            
        except Exception as e:
            logging.exception(f"Unexpected error getting status: {e}")
            return {"error": str(e)}
    
    def _state_enum_to_string(self, state_enum: int) -> str:
        """Convert a state enum value to a string"""
        states = {
            0: "UNKNOWN",
            1: "FOLLOWER",
            2: "CANDIDATE",
            3: "LEADER"
        }
        return states.get(state_enum, "UNKNOWN")