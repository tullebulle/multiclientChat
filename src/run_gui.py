"""
GUI Client Runner

This module provides the entry point for starting the chat application's
graphical user interface. It supports both the Custom Binary and JSON protocols
through command-line configuration.

Features:
- Protocol selection (JSON/Custom)
- Server connection configuration
- Command-line argument parsing
- Error handling for connection failures

Usage:
    python run_gui.py [--host HOST] [--port PORT] [--protocol {json,custom}]

Example:
    python run_gui.py --host localhost --port 9999 --protocol json
"""

import argparse
import os
import sys

# Add parent directory to Python path to handle imports when run from different locations
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from src.common.gui_client import ChatGUI

def main():
    """
    Main entry point for the GUI application.
    
    Parses command-line arguments and initializes the chat GUI with the
    specified configuration. Handles connection setup and protocol selection.
    
    Command-line Arguments:
        --host: Server hostname or IP (default: localhost)
        --port: Server port number (default: 9999)
        --protocol: Protocol to use (json/custom, default: custom)
        
    The function will exit with an error message if the connection fails
    or if invalid arguments are provided.
    """
    parser = argparse.ArgumentParser(description="Chat GUI client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=9999, help="Server port")
    parser.add_argument(
        "--protocol",
        choices=["json", "custom"],
        default="custom",
        help="Protocol to use"
    )
    args = parser.parse_args()
    
    try:
        client = ChatGUI(args.host, args.port, args.protocol)
        client.run()
    except KeyboardInterrupt:
        print("\nShutting down client...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 