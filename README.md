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

## Project Structure

The project is organized into the following directories:

- `src/`: Source code for the chat application
- `scripts/`: Scripts for cluster management and setup
- `tools/`: Diagnostic and testing tools
- `docs/`: Documentation and guides
- `logs/`: Server logs
- `data/`: Database files and storage

## Running with Raft Consensus

The application now includes a distributed consensus implementation using the Raft algorithm.

### Starting a Raft Cluster

To start a cluster with multiple nodes:

```bash
python scripts/start_cluster_mp.py start
```

To stop the cluster:

```bash
python scripts/start_cluster_mp.py stop
```

To reset the cluster (clear all data and restart):

```bash
python scripts/reset_cluster.py
```

### Testing Raft Consensus

For detailed testing instructions, see:

```bash
cat docs/testing_raft_consensus.md
```

Or run the diagnostic tool directly:

```bash
python tools/diagnose_replication.py
```


### Running the server and client
To run the server, use the following command from the root directory:

```bash
python src/run_server.py 
```

To run a client gui, use the following command from the root directory:
```bash
python src/run_gui.py
```

These commands take three optional arguments:
 1. --protocol, default is custom, takes values custom, json, or grpc. Specifies protocol of communication between server and client.
 2. --host, default is localhost. Specifies the server location.
 3. --port, default is 9999. Specifies the server port.


### Testing
Testing the gRPC protocol:
```bash
./src/grpc_protocol/tests/run_tests.sh
```

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
- Distributed consensus with Raft algorithm for high availability

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


## Attributions

We used Cursor to help us with implementation.

We also used the following websites to help us with the implementation:
- https://www.geeksforgeeks.org/tcp-server-client-implementation-in-python/
- https://www.geeksforgeeks.org/socket-programming-multi-threading-python/
- https://www.geeksforgeeks.org/socket-programming-in-python/
