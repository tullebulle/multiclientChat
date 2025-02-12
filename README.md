# multiclientChat


#####
To get started, clone the repository and run the server with the protocol of your choice.

```bash
git clone https://github.com/tullebulle/multiclientChat.git
cd multiclientChat
```

You need Python with TKinter installed to run the gui. To get this, you can use the following command:

```bash
sudo apt-get install python3-tk
```


#### Custom Protocol
To run the server with the custom protocol, use the following command from the root directory:

```bash
python src/run_server.py --protocol custom
```

To run a client gui, use the following command from the root directory:

```bash
python src/run_gui.py --protocol custom
```


#### JSON Protocol

To run the server with the JSON protocol, use the following command:

```bash
python src/run_server.py --protocol json
```
and run the gui client with the JSON protocol, use the following command:
```bash
python src/run_gui.py --protocol json
```




### Testing
Testing the custom protocol:
```bash
./src/custom_protocol/tests/run_tests.sh
```

Testing the JSON protocol:
```bash
./src/json_protocol/tests/run_tests.sh
```

Compare the test custom protocol and JSON protocol in terms of size and space:
```bash
python src/compare_protocols.py
```

## About the Application

This multiclient chat application demonstrates different approaches to client-server communication protocols. It features:

### Architecture
- Client-server architecture with support for multiple simultaneous connections
- Two protocol implementations: Custom Binary Protocol and JSON Protocol
- Graphical user interface built with Tkinter
- Thread-safe server implementation

### Features
- User account management (create, login, delete)
- Real-time messaging between users
- Message management (read/unread status, deletion)
- User search with pagination
- Auto-refresh for new messages
- Secure password handling with SHA-256 hashing

### Protocol Comparison
- **Custom Binary Protocol**: Optimized for efficiency with minimal overhead
  - Fixed-length headers
  - Binary message format
  - Compact data representation
  
- **JSON Protocol**: Focused on readability and flexibility
  - Human-readable format
  - Self-documenting structure
  - Easy to debug and extend

### Security Features
- Password hashing using SHA-256
- No plaintext password transmission
- Session-based authentication
- Secure message deletion

### Performance Considerations
- Efficient message delivery
- Pagination for large datasets
- Optimized refresh cycles
- Thread-safe operations

The application serves as a practical example of different protocol implementations and their trade-offs in a real-world messaging system.