"""
gRPC Chat Server Implementation

This module implements the server-side handling of the gRPC chat protocol.
It provides a high-performance, thread-safe server capable of handling multiple
simultaneous client connections using gRPC.
"""

import grpc
from concurrent import futures
import logging
import os
import time
import threading
import uuid
import json
from typing import Dict, List, Optional

from . import chat_pb2
from . import chat_pb2_grpc
from src.replication.persistence import PersistenceManager, CommandType
from src.replication.consensus import RaftNode, ServerState, NotLeaderError

class ChatServicer(chat_pb2_grpc.ChatServiceServicer):
    """
    Implementation of the ChatService gRPC service.
    
    This class implements all the RPC methods defined in the chat.proto file.
    It uses the PersistenceManager class for storing and retrieving data, ensuring
    data persistence across server restarts.

    It also integrates with the Raft consensus algorithm for fault tolerance.

    Attributes:
        raft_node: The RaftNode instance for consensus
        messages_lock: Lock for thread-safe message operations
        accounts_lock: Lock for thread-safe account operations
    """
    
    def __init__(self, db_path=None, node_id=None, peer_addresses=None):
        """
        Initialize the ChatServicer.
        
        Args:
            db_path: Path to the SQLite database file. If None, a UUID-based path will be used.
            node_id: ID of this node in the Raft cluster. If None, a UUID will be used.
            peer_addresses: Dictionary mapping peer node IDs to their addresses.
        """
        self.messages_lock = threading.Lock()
        self.account_lock = threading.Lock()
        
        # Set up persistence
        if db_path is None:
            # Create a unique database file if none specified
            db_path = f"{uuid.uuid4()}.db"
        
        # Set up Raft node
        if node_id is None:
            node_id = str(uuid.uuid4())
        
        if peer_addresses is None:
            peer_addresses = {}
        
        # Initialize Raft node with persistence manager
        self.raft_node = RaftNode(node_id=node_id, db_path=db_path, peer_addresses=peer_addresses)
        
        logging.info(f"Initialized ChatServicer with node_id={node_id}, db_path={db_path}, "
                    f"peers={list(peer_addresses.keys())}")
    
    def CreateAccount(self, request, context):
        """Create a new user account"""
        try:
            username = request.username
            password_hash = request.password_hash
            
            with self.account_lock:
                try:
                    # Only leaders can process write operations
                    success = self.raft_node.create_account(
                        username=username,
                        password_hash=password_hash
                    )
                    
                    if success:
                        logging.info(f"Created new account for user: {username}")
                        return chat_pb2.CreateAccountResponse(
                            success=True,
                            error_message=""
                        )
                    else:
                        error_message = f"Failed to create account: username '{username}' already exists"
                        logging.warning(error_message)
                        return chat_pb2.CreateAccountResponse(
                            success=False,
                            error_message=error_message
                        )
                except NotLeaderError as e:
                    # Forward the request to the leader instead of returning an error
                    response = self._forward_to_leader(request, "CreateAccount", context)
                    if response:
                        return response
                    
                    # If forwarding failed, return the original error
                    context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                    context.set_details(str(e))
                    return chat_pb2.CreateAccountResponse(
                        success=False,
                        error_message=f"Not the leader. Try {e.leader_id}"
                    )
        except Exception as e:
            logging.error(f"Error creating account: {e}")
            return chat_pb2.CreateAccountResponse(
                success=False,
                error_message=str(e)
            )
    
    def Authenticate(self, request, context):
        """Authenticate a user"""
        try:
            username = request.username
            password_hash = request.password_hash
            
            with self.account_lock:
                # Use the persistence manager directly for read-only operations
                success = self.raft_node.persistence.authenticate_user(
                    username=username,
                    password_hash=password_hash
                )
                
                if success:
                    logging.info(f"User authenticated successfully: {username}")
                    return chat_pb2.AuthResponse(
                        success=True,
                        error_message=""
                    )
                
            logging.warning(f"Failed authentication attempt for user: {username}")
            return chat_pb2.AuthResponse(
                success=False,
                error_message="Invalid username or password"
            )
            
        except Exception as e:
            logging.error(f"Authentication error: {e}")
            return chat_pb2.AuthResponse(
                success=False,
                error_message=str(e)
            )

    def SendMessage(self, request, context):
        """Send a message to another user"""
        username = self._get_username_from_metadata(context)
        if not username:
            return chat_pb2.SendMessageResponse(
                message_id=0,
                error_message="Not authenticated"
            )
            
        try:
            # First verify recipient exists (read-only operation)
            with self.account_lock:
                users = self.raft_node.persistence.list_users(request.recipient)
                if request.recipient not in users:
                    return chat_pb2.SendMessageResponse(
                        message_id=0,
                        error_message="Recipient does not exist"
                    )
            
            # Forward to leader if this node is not the leader
            try:
                message_id = self.raft_node.send_message(
                    sender=username,
                    recipient=request.recipient,
                    content=request.content
                )
                
                if message_id > 0:
                    return chat_pb2.SendMessageResponse(
                        message_id=message_id,
                        error_message=""
                    )
                else:
                    return chat_pb2.SendMessageResponse(
                        message_id=0,
                        error_message="Failed to send message"
                    )
            except NotLeaderError as e:
                # Forward the request to the leader instead of returning an error
                response = self._forward_to_leader(request, "SendMessage", context)
                if response:
                    return response
                
                # If forwarding failed, return the original error
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details(str(e))
                return chat_pb2.SendMessageResponse(
                    message_id=0,
                    error_message=f"Not the leader. Try {e.leader_id}"
                )
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            return chat_pb2.SendMessageResponse(
                message_id=0,
                error_message=str(e)
            )

    def GetMessages(self, request: chat_pb2.GetMessagesRequest, context: grpc.ServicerContext) -> chat_pb2.GetMessagesResponse:
        """
        Get messages for the authenticated user.
        """
        username = self._get_username_from_metadata(context)
        if not username:
            return chat_pb2.GetMessagesResponse(
                messages=[],
                error_message="Not authenticated"
            )

        try:
            with self.messages_lock:
                # Read-only operation, use persistence manager directly
                messages_data = self.raft_node.persistence.get_messages(
                    username=username,
                    include_read=request.include_read
                )
                
                # Convert to protocol buffer messages
                pb_messages = []
                for msg in messages_data:
                    pb_messages.append(chat_pb2.Message(
                        id=msg['id'],
                        sender=msg['sender'],
                        recipient=msg['recipient'],
                        content=msg['content'],
                        timestamp=msg['timestamp'],
                        is_read=msg['is_read']
                    ))
                
                return chat_pb2.GetMessagesResponse(
                    messages=pb_messages,
                    error_message=""
                )
        
        
        except Exception as e:
            logging.error(f"Error getting messages: {e}")
            return chat_pb2.GetMessagesResponse(
                messages=[],
                error_message=str(e)
            )

    def _get_username_from_metadata(self, context: grpc.ServicerContext) -> str:
        """
        Extract username from the request metadata.
        
        Args:
            context: gRPC context containing metadata
            
        Returns:
            str: Username from metadata or empty string if not found
        """
        metadata = dict(context.invocation_metadata())
        return metadata.get('username', '')

    def MarkRead(self, request: chat_pb2.MarkReadRequest, context: grpc.ServicerContext) -> chat_pb2.MarkReadResponse:
        """Mark messages as read"""
        username = self._get_username_from_metadata(context)
        if not username:
            return chat_pb2.MarkReadResponse(
                success=False,
                error_message="Not authenticated"
            )
        
        try:
            # Forward to leader if this node is not the leader
            try:
                success = self.raft_node.mark_messages_read(
                    username=username,
                    message_ids=list(request.message_ids)
                )
                
                if success:
                    return chat_pb2.MarkReadResponse(
                        success=True,
                        error_message=""
                    )
                else:
                    return chat_pb2.MarkReadResponse(
                        success=False,
                        error_message="Failed to mark messages as read"
                    )
            except NotLeaderError as e:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details(str(e))
                return chat_pb2.MarkReadResponse(
                    success=False,
                    error_message=f"Not the leader. Try {e.leader_id}"
                )
        except Exception as e:
            logging.error(f"Error marking messages as read: {e}")
            return chat_pb2.MarkReadResponse(
                success=False,
                error_message=str(e)
            )

    def DeleteMessages(self, request: chat_pb2.DeleteMessagesRequest, context: grpc.ServicerContext) -> chat_pb2.DeleteMessagesResponse:
        """Delete messages"""
        username = self._get_username_from_metadata(context)
        if not username:
            return chat_pb2.DeleteMessagesResponse(
                success=False,
                error_message="Not authenticated"
            )
        
        try:
            # Forward to leader if this node is not the leader
            try:
                success = self.raft_node.delete_messages(
                    username=username,
                    message_ids=list(request.message_ids)
                )
                
                if success:
                    return chat_pb2.DeleteMessagesResponse(
                        success=True,
                        error_message=""
                    )
                else:
                    return chat_pb2.DeleteMessagesResponse(
                        success=False,
                        error_message="No messages found to delete"
                    )
            except NotLeaderError as e:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details(str(e))
                return chat_pb2.DeleteMessagesResponse(
                    success=False,
                    error_message=f"Not the leader. Try {e.leader_id}"
                )
        except Exception as e:
            logging.error(f"Error deleting messages: {e}")
            return chat_pb2.DeleteMessagesResponse(
                success=False,
                error_message=str(e)
            )

    def ListAccounts(self, request: chat_pb2.ListAccountsRequest, context: grpc.ServicerContext) -> chat_pb2.ListAccountsResponse:
        """List user accounts matching pattern"""
        try:
            with self.account_lock:
                # Read-only operation, use persistence manager directly
                pattern = request.pattern if request.pattern else "*"
                usernames = self.raft_node.persistence.list_users(pattern)
                
                return chat_pb2.ListAccountsResponse(
                    usernames=usernames,
                    error_message=""
                )
        except Exception as e:
            logging.error(f"Error listing accounts: {e}")
            return chat_pb2.ListAccountsResponse(
                usernames=[],
                error_message=str(e)
            )

    def DeleteAccount(self, request: chat_pb2.DeleteAccountRequest, context: grpc.ServicerContext) -> chat_pb2.DeleteAccountResponse:
        """Delete a user account"""
        try:
            username = request.username
            password_hash = request.password_hash
            
            with self.account_lock:
                # First authenticate the user
                if not self.raft_node.persistence.authenticate_user(username, password_hash):
                    return chat_pb2.DeleteAccountResponse(
                        success=False,
                        error_message="Invalid username or password"
                    )
            
            # Forward to leader if this node is not the leader
            try:
                success = self.raft_node.delete_account(username)
                
                if success:
                    logging.info(f"Deleted account for user: {username}")
                    return chat_pb2.DeleteAccountResponse(
                        success=True,
                        error_message=""
                    )
                else:
                    return chat_pb2.DeleteAccountResponse(
                        success=False,
                        error_message="Failed to delete account"
                    )
            except NotLeaderError as e:
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details(str(e))
                return chat_pb2.DeleteAccountResponse(
                    success=False,
                    error_message=f"Not the leader. Try {e.leader_id}"
                )
        except Exception as e:
            logging.error(f"Error deleting account: {e}")
            return chat_pb2.DeleteAccountResponse(
                success=False,
                error_message=str(e)
            )
    
    def GetUnreadCount(self, request: chat_pb2.UnreadCountRequest, context: grpc.ServicerContext) -> chat_pb2.UnreadCountResponse:
        """Get count of unread messages for a user"""
        username = self._get_username_from_metadata(context)
        if not username:
            return chat_pb2.UnreadCountResponse(
                count=0,
                error_message="Not authenticated"
            )
            
        try:
            with self.messages_lock:
                # Read-only operation, use persistence manager directly
                count = self.raft_node.persistence.get_unread_count(username)
                
                return chat_pb2.UnreadCountResponse(
                    count=count,
                    error_message=""
                )
        except Exception as e:
            logging.error(f"Error getting unread count: {e}")
            return chat_pb2.UnreadCountResponse(
                count=0,
                error_message=str(e)
            )
    
    def RequestVote(self, request: chat_pb2.RequestVoteRequest, context: grpc.ServicerContext) -> chat_pb2.RequestVoteResponse:
        """Handle INCOMING RequestVote RPC from Raft"""
        try:
            # Use the correctly named method for handling incoming vote requests
            current_term, vote_granted = self.raft_node.handle_incoming_vote_request(
                term=request.term,
                candidate_id=request.candidate_id,
                last_log_index=request.last_log_index,
                last_log_term=request.last_log_term
            )
            
            # Return the response
            return chat_pb2.RequestVoteResponse(
                term=current_term,
                vote_granted=vote_granted
            )
        except Exception as e:
            logging.error(f"Error processing RequestVote: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return chat_pb2.RequestVoteResponse(
                term=self.raft_node.current_term,
                vote_granted=False
            )
    
    def AppendEntries(self, request: chat_pb2.AppendEntriesRequest, context: grpc.ServicerContext) -> chat_pb2.AppendEntriesResponse:
        """Handle AppendEntries RPC from Raft"""
        try:
            # Convert protobuf entries to dictionaries
            entries = []
            for pb_entry in request.entries:
                entry = {
                    'index': pb_entry.index,
                    'term': pb_entry.term,
                    'command_type': CommandType(pb_entry.command_type),
                    'data': json.loads(pb_entry.data)
                }
                entries.append(entry)
            
            # Forward the request to the RaftNode
            current_term, success = self.raft_node.append_entries(
                term=request.term,
                leader_id=request.leader_id,
                prev_log_index=request.prev_log_index,
                prev_log_term=request.prev_log_term,
                entries=entries,
                leader_commit=request.leader_commit
            )
            
            # Return the response
            last_index, _ = self.raft_node.persistence.get_last_log_index_and_term()
            return chat_pb2.AppendEntriesResponse(
                term=current_term,
                success=success,
                match_index=last_index
            )
        except Exception as e:
            logging.error(f"Error processing AppendEntries: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return chat_pb2.AppendEntriesResponse(
                term=self.raft_node.current_term,
                success=False,
                match_index=0
            )
    
    def GetClusterStatus(self, request: chat_pb2.ClusterStatusRequest, context: grpc.ServicerContext) -> chat_pb2.ClusterStatusResponse:
        """Get status of the Raft cluster"""
        try:
            # Get status information from the RaftNode
            last_index, _ = self.raft_node.persistence.get_last_log_index_and_term()
            
            state_map = {
                ServerState.FOLLOWER: "FOLLOWER",
                ServerState.CANDIDATE: "CANDIDATE",
                ServerState.LEADER: "LEADER"
            }
            
            # Return the response
            return chat_pb2.ClusterStatusResponse(
                node_id=self.raft_node.node_id,
                state=state_map.get(self.raft_node.state, "UNKNOWN"),
                current_term=self.raft_node.current_term,
                leader_id=self.raft_node.leader_id or "",
                commit_index=self.raft_node.commit_index,
                last_applied=self.raft_node.last_applied,
                peer_count=len(self.raft_node.peer_addresses),
                log_count=last_index
            )
        except Exception as e:
            logging.error(f"Error getting cluster status: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return chat_pb2.ClusterStatusResponse(
                node_id=self.raft_node.node_id,
                state="ERROR",
                current_term=0,
                leader_id="",
                commit_index=0,
                last_applied=0,
                peer_count=0,
                log_count=0
            )

    def GetStatus(self, request, context):
        """Get detailed status information about this server node"""
        try:
            with self.account_lock:
                # Get status information from the Raft node
                state = None
                if self.raft_node.state == ServerState.FOLLOWER:
                    state = chat_pb2.StatusResponse.ServerState.FOLLOWER
                elif self.raft_node.state == ServerState.CANDIDATE:
                    state = chat_pb2.StatusResponse.ServerState.CANDIDATE
                elif self.raft_node.state == ServerState.LEADER:
                    state = chat_pb2.StatusResponse.ServerState.LEADER
                else:
                    state = chat_pb2.StatusResponse.ServerState.UNKNOWN
                
                return chat_pb2.StatusResponse(
                    state=state,
                    current_term=self.raft_node.current_term,
                    leader_id=self.raft_node.leader_id or "",
                    commit_index=self.raft_node.commit_index,
                    last_applied=self.raft_node.last_applied,
                    error_message=""
                )
        except Exception as e:
            logging.error(f"Error getting status: {e}")
            return chat_pb2.StatusResponse(
                state=chat_pb2.StatusResponse.ServerState.UNKNOWN,
                error_message=str(e)
            )

    def _forward_to_leader(self, request, method_name, context):
        """
        Forward a request to the current leader.
        
        Args:
            request: The original gRPC request
            method_name: Name of the gRPC method to call on the leader
            context: The original gRPC context
            
        Returns:
            The response from the leader
        """
        # Check if we know who the leader is
        if not self.raft_node.leader_id:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("No known leader")
            return None
        
        # Get leader address
        leader_id = self.raft_node.leader_id
        if leader_id not in self.raft_node.peer_addresses:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Leader {leader_id} address not in peer list")
            return None
        
        leader_address = self.raft_node.peer_addresses[leader_id]
        
        # Forward the request to the leader
        try:
            logging.info(f"Forwarding {method_name} request to leader {leader_id} at {leader_address}")
            
            # Create a channel and stub for leader
            channel = grpc.insecure_channel(leader_address)
            stub = chat_pb2_grpc.ChatServiceStub(channel)
            
            # Get the appropriate method from the stub
            forward_method = getattr(stub, method_name)
            
            # Forward any authentication metadata
            metadata = []
            for key, value in context.invocation_metadata():
                if key == 'username':
                    metadata.append(('username', value))
            
            # Call the method on the leader with the original request
            response = forward_method(request, metadata=metadata)
            
            # Close the channel
            channel.close()
            
            return response
            
        except Exception as e:
            logging.error(f"Error forwarding request to leader: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Error forwarding to leader: {str(e)}")
            return None

    # def GetClusterMembers(self, request: chat_pb2.ClusterMembersRequest, context: grpc.ServicerContext) -> chat_pb2.ClusterMembersResponse:
    #     """
    #     Get information about all servers in the cluster.
        
    #     This includes server addresses, availability status, and which one is the leader.
    #     """
    #     try:
    #         # Get cluster members from the Raft node
    #         members = self.raft_node.get_cluster_members()
            
    #         # Convert to protocol buffer format
    #         pb_members = []
    #         for node_id, info in members.items():
    #             pb_member = chat_pb2.ServerInfo(
    #                 node_id=node_id,
    #                 address=info['address'],
    #                 is_available=info['is_available'],
    #                 is_leader=info['is_leader']
    #             )
    #             pb_members.append(pb_member)
            
    #         return chat_pb2.ClusterMembersResponse(
    #             servers=pb_members,
    #             error_message=""
    #         )
    #     except Exception as e:
            logging.error(f"Error getting cluster members: {e}")
            return chat_pb2.ClusterMembersResponse(
                servers=[],
                error_message=str(e)
            )

# def serve(port=50051):
#     """
#     Start the gRPC server.
    
#     Args:
#         port: Port number to listen on
        
#     The server runs until interrupted, handling requests using
#     the ChatServicer implementation.
#     """
#     server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
#     chat_pb2_grpc.add_ChatServiceServicer_to_server(
#         ChatServicer(), server
#     )
#     server.add_insecure_port(f'[::]:{port}')
#     server.start()
    
#     logging.info(f"gRPC Server started on port {port}")
    
#     try:
#         while True:
#             time.sleep(86400)  # One day in seconds
#     except KeyboardInterrupt:
#         server.stop(0)
#         logging.info("Server stopped")

# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     serve() 