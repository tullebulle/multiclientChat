"""
GUI Client Runner

Starts the GUI client with the specified protocol.
"""

import argparse
import os
import sys

# Add parent directory to Python path to handle imports when run from different locations
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)
from src.custom_protocol.gui_client import ChatGUI
from src.json_protocol.gui_client import JSONChatGUIClient

def main():
    parser = argparse.ArgumentParser(description="Chat GUI client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument(
        "--protocol",
        choices=["json", "custom"],
        default="custom",
        help="Protocol to use"
    )
    args = parser.parse_args()
    
    try:
        if args.protocol == "custom":
            client = ChatGUI(args.host)
        else:
            client = JSONChatGUIClient(args.host)
        client.run()
        
    except KeyboardInterrupt:
        print("\nShutting down client...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 