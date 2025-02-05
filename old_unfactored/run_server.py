"""
Chat Server Runner

Starts the chat server and keeps it running until interrupted.
"""

from server import ThreadedTCPServer, ChatRequestHandler
import logging
import argparse

def main():
    """Main entry point for the chat server"""
    parser = argparse.ArgumentParser(description="Chat server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=9999, help="Server port")
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Create and start server
    server = ThreadedTCPServer((args.host, args.port), ChatRequestHandler)
    try:
        logging.info(f"Server starting on {args.host}:{args.port}")
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("Server shutting down...")
        server.shutdown()
        server.server_close()

if __name__ == "__main__":
    main() 