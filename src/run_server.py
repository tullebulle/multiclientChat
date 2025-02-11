"""
Chat Server Runner

Starts the chat server with the specified protocol.
"""

import argparse
import logging
import signal
import sys
import threading
import os
# Add parent directory to Python path to handle imports when run from different locations
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from src.json_protocol.server import JSONChatServer
from src.custom_protocol.server import CustomChatServer

def shutdown_servers(servers):
    """Shutdown all servers gracefully"""
    logging.info("Shutting down servers...")
    for server in servers:
        server.shutdown()
        server.server_close()

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    print("\nShutting down server...")
    # We can't call sys.exit() directly as it doesn't allow cleanup
    # Instead, we'll raise KeyboardInterrupt to trigger the cleanup in main()
    raise KeyboardInterrupt()

def main():
    """Main entry point for the chat server"""
    parser = argparse.ArgumentParser(description="Chat server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=9999, help="Server port for custom protocol")
    parser.add_argument(
        "--protocol",
        choices=["json", "custom", "both"],
        default="custom",
        help="Protocol to use (json, custom, or both)"
    )
    
    # Remove json-port argument since it's always 9998
    parser.add_argument(
        "--custom-port",
        type=int,
        default=9999,
        help="Port for custom protocol when running both"
    )
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal_handler)
    
    servers = []
    server_threads = []
    
    try:
        if args.protocol in ["custom", "both"]:
            custom_port = 9999
            custom_server = CustomChatServer((args.host, custom_port))
            servers.append(custom_server)
            logging.info(f"Custom protocol server starting on {args.host}:{custom_port}")
            
        if args.protocol in ["json", "both"]:
            # Always use port 9998 for JSON
            json_server = JSONChatServer((args.host, 9998))
            servers.append(json_server)
            logging.info(f"JSON protocol server starting on {args.host}:9998")
        
        # Start all servers in separate threads
        for server in servers:
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            server_threads.append(thread)
            
        # Keep main thread running
        while True:
            for thread in server_threads:
                if not thread.is_alive():
                    raise Exception("Server thread died unexpectedly")
            threading.Event().wait(1.0)  # More efficient than time.sleep(1)
            
    except KeyboardInterrupt:
        shutdown_servers(servers)
        # Wait for threads to finish
        for thread in server_threads:
            thread.join(timeout=5.0)
        logging.info("Server shutdown complete")
        
    except Exception as e:
        logging.error(f"Error running server: {e}")
        shutdown_servers(servers)
        sys.exit(1)

if __name__ == "__main__":
    main() 