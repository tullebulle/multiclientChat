"""
gRPC GUI Chat Client
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
import sys
from datetime import datetime
import argparse
from ..common.gui_client import ChatGUI
from .client_grpc import GRPCChatClient

# Configure logging to show in both file and console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('grpc_client.log'),  # Log to file
        logging.StreamHandler(sys.stdout)        # Log to console
    ]
)

logger = logging.getLogger(__name__)

class GRPCChatGUI(ChatGUI):
    """GUI for gRPC chat client"""
    
    def __init__(self, host="localhost", port=50051):
        """Initialize with gRPC client"""
        logger.info("Starting gRPC Chat GUI")
        self.client = GRPCChatClient(host=host, port=port)
        self.protocol = "grpc"
        
        if not self.client.connect():
            error_msg = "Could not connect to gRPC server!"
            logger.error(error_msg)
            messagebox.showerror("Connection Error", error_msg)
            return
            
        logger.info(f"Connected to gRPC server at {host}:{port}")
        
        # Main window setup
        self.root = tk.Tk()
        self.root.title("gRPC Chat Application")
        self.root.geometry("800x600")
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create tabs
        self.login_frame = self.create_login_tab()
        self.chat_frame = self.create_chat_tab()
        
        # Initially disable chat tab
        self.notebook.tab(1, state='disabled')
        
        # Add refresh interval (in milliseconds)
        self.refresh_interval = 1000
        self.schedule_refresh()
        
        # Initialize message tracking
        self.message_ids = {}
        self.current_page = 1
        self.page_size = 100
        
        logger.info("GUI initialization complete")

    def refresh_messages(self):
        """Manually refresh messages while preserving selection"""
        if not self.client.current_user:
            return
        
        try:
            messages = self.client.get_messages(include_read=True)
            
            # Store currently selected items before refresh
            selected_items = self.message_list.selection()
            selected_contents = {
                self.message_list.item(item)['values'][2]: item  # Using message content as key
                for item in selected_items
            }
            
            # Clear existing messages
            for item in self.message_list.get_children():
                self.message_list.delete(item)
            self.message_ids.clear()
            
            # Sort messages by timestamp and limit the number shown
            limit = int(self.message_limit.get())
            sorted_messages = sorted(messages, key=lambda x: x['timestamp'])
            recent_messages = sorted_messages[-limit:]
            
            # Calculate wrap width based on Message column width
            message_col_width = self.message_list.column('Message', 'width')
            chars_per_line = message_col_width // 7  # Approximate characters that fit per line
            
            new_selections = []  # Store new item IDs to select
            
            # Add messages to treeview with dynamic word wrapping
            for msg in recent_messages:
                # Convert integer timestamp to datetime
                timestamp = datetime.fromtimestamp(msg['timestamp']).strftime('%H:%M:%S')
                content = msg['content']
                
                # Word wrap the content
                words = content.split()
                lines = []
                current_line = []
                current_length = 0
                
                for word in words:
                    word_length = len(word)
                    if current_length + word_length + 1 <= chars_per_line:
                        current_line.append(word)
                        current_length += word_length + 1
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                        current_length = word_length
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                wrapped_content = '\n'.join(lines)
                
                item_id = self.message_list.insert('', 'end',
                    values=(timestamp, msg['sender'], wrapped_content),
                    tags=('unread' if not msg['is_read'] else 'read',))
                self.message_ids[item_id] = msg['id']
                
                # If this message was previously selected, add it to new selections
                if wrapped_content in selected_contents:
                    new_selections.append(item_id)
            
            # Restore selections
            for item_id in new_selections:
                self.message_list.selection_add(item_id)
            
        except Exception as e:
            logging.error(f"Error refreshing messages: {e}")
            messagebox.showerror("Error", "Failed to refresh messages")

    def handle_delete_account(self):
        """Handle delete account button click"""
        logger = logging.getLogger(__name__)
        logger.info("Delete account button clicked")
        
        username = self.delete_username.get().strip()
        password = self.delete_password.get().strip()
        logger.debug(f"Attempting to delete account for user: {username}")
        
        if not username or not password:
            logger.warning("Delete account failed: Missing username or password")
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        # Try to login as the user to check messages
        temp_client = None
        if self.client.current_user != username:
            logger.debug("Creating temporary client for message check")
            # Create temporary client with same protocol
            temp_client = GRPCChatClient(host=self.client.host, port=self.client.port)
            
            if not temp_client.connect() or not temp_client.login(username, password):
                logger.error(f"Failed to verify account for user: {username}")
                messagebox.showerror("Error", "Failed to verify account. Please check your credentials.")
                return
            messages = temp_client.get_messages(include_read=False)
        else:
            logger.debug("Using existing client for message check")
            messages = self.client.get_messages(include_read=False)
        
        # Check for unread messages
        if messages:
            logger.info(f"Account has {len(messages)} unread messages")
            if not messagebox.askyesno("Warning", 
                                      f"This account has {len(messages)} unread messages!\n"
                                      "Are you sure you want to delete your account?\n"
                                      "This action cannot be undone!"):
                logger.info("User cancelled deletion due to unread messages")
                if temp_client:
                    temp_client.disconnect()
                return
        else:
            # Regular confirmation for deletion without unread messages
            if not messagebox.askyesno("Confirm Delete", 
                                      "Are you sure you want to delete your account?\n"
                                      "This action cannot be undone!"):
                logger.info("User cancelled deletion")
                if temp_client:
                    temp_client.disconnect()
                return
        
        logger.info(f"Proceeding with account deletion for user: {username}")
        if self.client.delete_account(username, password):
            logger.info(f"Successfully deleted account: {username}")
            messagebox.showinfo("Success", "Account deleted successfully")
            self.delete_username.delete(0, tk.END)
            self.delete_password.delete(0, tk.END)
        else:
            logger.error(f"Failed to delete account for user: {username}")
            messagebox.showerror("Error", "Failed to delete account")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="gRPC Chat GUI client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=50051, help="Server port")
    args = parser.parse_args()
    
    logger.info(f"Starting client with host={args.host}, port={args.port}")
    gui = GRPCChatGUI(host=args.host, port=args.port)
    gui.run()

if __name__ == "__main__":
    main() 