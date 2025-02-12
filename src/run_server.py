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

def shutdown_server(server):
    """Shutdown server gracefully"""
    logging.info("Shutting down server...")
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
    parser.add_argument("--port", type=int, default=9999, help="Server port")
    parser.add_argument(
        "--protocol",
        choices=["json", "custom"],
        default="custom",
        help="Protocol to use (json or custom)"
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Handle Ctrl+C gracefully
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        if args.protocol == "custom":
            server = CustomChatServer((args.host, args.port))
            logging.info(f"Custom protocol server starting on {args.host}:{args.port}")
            
        if args.protocol == "json":
            server = JSONChatServer((args.host, args.port))
            logging.info(f"JSON protocol server starting on {args.host}:{args.port}")
        
        # Start all servers in separate threads
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

if __name__ == "__main__":
    main() 