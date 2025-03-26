"""
Chat Server Runner

This module provides the entry point for starting the chat server with the
specified protocol implementation. It supports both the Custom Binary and
JSON protocols through command-line configuration.

Features:
- Protocol selection (JSON/Custom/gRPC)
- Server configuration (host/port)
- Persistence configuration (database path)
- Raft consensus configuration (node ID, peer addresses)
- Graceful shutdown handling
- Signal handling (Ctrl+C)
- Logging configuration

Usage:
    python run_server.py [--host HOST] [--port PORT] [--protocol {json,custom,grpc}] 
                         [--db-path PATH] [--node-id ID] [--peer NODE_ID:HOST:PORT] ...

Example:
    # Run a standalone server
    python run_server.py --protocol grpc --port 9001 --db-path ./chat_data.db
    
    # Run a cluster of servers
    # First server:
    python run_server.py --protocol grpc --port 9001 --node-id node1 --db-path ./data/node1 \
                         --peer node2:localhost:9002 --peer node3:localhost:9003
                         
    # Second server:
    python run_server.py --protocol grpc --port 9002 --node-id node2 --db-path ./data/node2 \
                         --peer node1:localhost:9001 --peer node3:localhost:9003
                         
    # Third server:
    python run_server.py --protocol grpc --port 9003 --node-id node3 --db-path ./data/node3 \
                         --peer node1:localhost:9001 --peer node2:localhost:9002
"""

import argparse
import logging
import signal
import sys
import threading
import os
import time
import grpc

# Add parent directory to Python path to handle imports when run from different locations
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.json_protocol.server import JSONChatServer
from src.custom_protocol.server import CustomChatServer
from src.grpc_protocol import chat_pb2_grpc
from concurrent import futures
from src.grpc_protocol.server import ChatServicer


def shutdown_server(server):
    """
    Shutdown server gracefully.
    
    Args:
        server: The server instance to shut down
        
    Performs a clean shutdown by:
    1. Stopping the server from accepting new connections
    2. Closing existing connections
    3. Releasing server resources
    """
    logging.info("Shutting down server...")
    server.shutdown()
    server.server_close()

def signal_handler(sig, frame):
    """
    Handle Ctrl+C gracefully.
    
    Args:
        sig: Signal number
        frame: Current stack frame
        
    Raises KeyboardInterrupt to trigger the cleanup in main()
    instead of calling sys.exit() directly, allowing for proper cleanup.
    """
    print("\nShutting down server...")
    # We can't call sys.exit() directly as it doesn't allow cleanup
    # Instead, we'll raise KeyboardInterrupt to trigger the cleanup in main()
    raise KeyboardInterrupt()

def parse_peer_arg(peer_str):
    """
    Parse a peer argument in the format 'node_id:host:port'.
    
    Args:
        peer_str: The peer string in the format 'node_id:host:port'
        
    Returns:
        Tuple[str, str]: (node_id, address) where address is 'host:port'
    """
    parts = peer_str.split(':')
    if len(parts) != 3:
        raise ValueError(f"Invalid peer format: {peer_str}, expected 'node_id:host:port'")
    
    node_id = parts[0]
    host = parts[1]
    port = parts[2]
    
    try:
        port = int(port)
    except ValueError:
        raise ValueError(f"Invalid port in peer: {port}")
    
    return node_id, f"{host}:{port}"

def main():
    """
    Main entry point for the chat server.
    
    Parses command-line arguments, initializes the appropriate server type,
    and handles the server lifecycle including startup and shutdown.
    
    Command-line Arguments:
        --host: Server hostname or IP (default: localhost)
        --port: Server port number (default: 9999)
        --protocol: Protocol to use (json/custom/grpc, default: custom)
        --db-path: Path to the database file for persistence (default: auto-generated)
        --node-id: ID of this node in the Raft cluster (default: auto-generated)
        --peer: Peer server address in the format 'node_id:host:port' (can be specified multiple times)
        
    The server runs until interrupted by Ctrl+C, at which point it performs
    a graceful shutdown.
    """
    parser = argparse.ArgumentParser(description="Chat server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=9999, help="Server port")
    parser.add_argument(
        "--protocol",
        choices=["json", "custom", "grpc"],
        default="grpc",
        help="Protocol to use (json, custom, or grpc)"
    )
    parser.add_argument(
        "--db-path",
        help="Path to the database file for persistence (for gRPC protocol only)"
    )
    parser.add_argument(
        "--node-id",
        help="ID of this node in the Raft cluster (for gRPC protocol only)"
    )
    parser.add_argument(
        "--peer",
        action="append",
        help="Peer server address in the format 'node_id:host:port' (can be specified multiple times)"
    )
    parser.add_argument(
        "--data-dir",
        help="Directory to store data files (for gRPC protocol only, will create a subdirectory using node-id)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal_handler)
    
    # Socket based protocols
    if args.protocol in ["custom", "json"]:
        try:
            if args.protocol == "custom":
                server = CustomChatServer((args.host, args.port))
                logging.info(f"Custom protocol server starting on {args.host}:{args.port}")
                
            elif args.protocol == "json":
                server = JSONChatServer((args.host, args.port))
                logging.info(f"JSON protocol server starting on {args.host}:{args.port}")
            
            # Start server in separate thread
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
                
            # Keep main thread running
            while True:
                if not thread.is_alive():
                    raise Exception("Server thread died unexpectedly")
                threading.Event().wait(1.0)  # More efficient than time.sleep(1)
                
        except KeyboardInterrupt:
            shutdown_server(server)
            # Wait for threads to finish
            thread.join(timeout=5.0)
            logging.info("Server shutdown complete")
            
        except Exception as e:
            logging.error(f"Error running server: {e}")
            shutdown_server(server)
            thread.join(timeout=5.0)
            logging.info("Server shutdown complete")
            sys.exit(1)

    # gRPC protocol
    elif args.protocol == "grpc":
        try:
            # Handle paths for data
            db_path = args.db_path
            if not db_path and args.data_dir and args.node_id:
                # Create a data directory for this node
                node_dir = os.path.join(args.data_dir, args.node_id)
                os.makedirs(node_dir, exist_ok=True)
                db_path = os.path.join(node_dir, "chat.db")
            
            # Parse peer addresses
            peer_addresses = {}
            if args.peer:
                for peer_str in args.peer:
                    try:
                        node_id, address = parse_peer_arg(peer_str)
                        peer_addresses[node_id] = address
                        logging.info(f"Added peer: {node_id} at {address}")
                    except ValueError as e:
                        logging.error(f"Invalid peer address: {e}")
            
            # Initialize server
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            server_address = f'{args.host}:{args.port}'
            
            # Initialize ChatServicer with database path and Raft configuration
            servicer = ChatServicer(
                db_path=db_path,
                address=server_address,
                node_id=args.node_id,
                peer_addresses=peer_addresses
            )
            
            chat_pb2_grpc.add_ChatServiceServicer_to_server(
                servicer, server
            )
            
            # Start the server
            
            server.add_insecure_port(server_address)
            server.start()
            
            # Log server information
            logging.info(f"gRPC protocol server started on {server_address}")
            if args.node_id:
                logging.info(f"Node ID: {args.node_id}")
            if db_path:
                logging.info(f"Using database at {db_path}")
            
            # Keep the server running until interrupted
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                # Shutdown the Raft node first
                if hasattr(servicer, 'raft_node'):
                    servicer.raft_node.shutdown()
                
                # Stop the gRPC server
                server.stop(0)
                logging.info("Server shutdown complete")

        except Exception as e:
            logging.error(f"Error running server: {e}")
            if server:
                # Shutdown the Raft node first
                if hasattr(servicer, 'raft_node'):
                    servicer.raft_node.shutdown()
                
                # Stop the gRPC server
                server.stop(0)
            logging.info("Server shutdown complete")
            sys.exit(1)

if __name__ == "__main__":
    main() 