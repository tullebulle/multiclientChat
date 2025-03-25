# Testing the Raft Consensus Implementation

This document provides a guide for testing the fixed Raft consensus implementation in our distributed chat application.

## Prerequisites

Before testing, ensure you have:
- All dependencies installed
- Clean storage directories for each node

## Testing Process

### 1. Basic Cluster Management

```bash
# Reset logs and storage (this will also start the cluster)
python scripts/reset_cluster.py
```

These commands ensure a clean test environment and start the cluster with sufficient delay between nodes to allow proper initialization.

### 2. Basic Replication Test

```bash
# Test user creation and verify replication
python tools/diagnose_replication.py
```


### 3. Manage specific nodes
```
python scripts/manage_node.py status
```

```
python scripts/manage_node.py kill --node node1
```

```
python scripts/manage_node.py revive --node node1
```


This runs a diagnostic test that:
- Identifies the current leader
- Creates a test user
- Waits for replication to complete
- Verifies the user exists on all nodes
- Reports the change in commit/apply indices

A successful test shows:
- All nodes showing the same commit_index and last_applied values
- The test user appearing in the user list of all nodes
- A "REPLICATION SUCCESS" message

### 3. Testing Message Replication

```bash
# Test message sending and verify replication
python tools/diagnose_replication.py --operation send_message
```

This more complex test:
- Creates two test users (alice and bob)
- Logs in as alice
- Sends a message to bob
- Verifies both users exist on all nodes
- Checks the commit indices are synchronized

### 4. Stability Testing

```bash
# Run multiple operations in sequence to test stability
for i in {1..5}; do python tools/diagnose_replication.py; done
```

This command runs the basic diagnostic test 5 times in succession to verify that:
- The system remains stable across multiple operations
- Leadership is maintained
- Entries continue to be properly replicated
- No state inconsistencies develop over time

### 5. Testing with the Chat UI

```bash
# In one terminal, start the cluster
python scripts/start_cluster_mp.py start

# In another terminal, start the UI
python src/run_gui.py
```

To verify proper operation in the UI:
1. Create multiple user accounts
2. Send messages between accounts
3. Log out and log back in with different accounts
4. Try accessing the system through different nodes

## Debugging Tools

If issues occur, these commands can help identify the problem:

```bash
# View logs for a specific server
tail -n 50 logs/server1.log
tail -n 50 logs/server2.log
tail -n 50 logs/server3.log

# Run with more verbose output
python tools/diagnose_replication.py --verbose
```

## Key Fixes Implemented

The main issues that were fixed:

1. **Type Error Fix**: Proper handling of CommandType enum conversion
   - Converting CommandType enum to integer values for network transmission
   - Converting integers back to CommandType when receiving entries

2. **Improved Error Handling**: Better recovery from replication failures

3. **Process Management**: Fixed startup timing issues between nodes

## Common Issues

If you encounter problems, check for:

1. **Type Conversion Issues**: Ensure any enum or complex types are properly serialized
2. **Network Connection Failures**: Check if nodes can connect to each other
3. **Log Conflicts**: Examine logs for mismatches in log entries
4. **State Inconsistencies**: Compare commit_index and last_applied across nodes 