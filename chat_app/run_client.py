"""
Chat Client Runner

Starts the chat client with the specified protocol.
"""

import argparse
from chat_app.custom_protocol.client import CustomChatClient
from chat_app.json_protocol.client import JSONChatClient

def main():
    parser = argparse.ArgumentParser(description="Chat client")
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
        if args.protocol == "custom":
            client = CustomChatClient(args.host, args.port)
        else:
            client = JSONChatClient(args.host, args.port)
            
        if client.connect():
            try:
                client.main_loop()
            finally:
                client.disconnect()
        
    except KeyboardInterrupt:
        print("\nShutting down client...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 