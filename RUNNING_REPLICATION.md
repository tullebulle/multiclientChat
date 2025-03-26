# Starting up with multiple servers

## Running Server
As before, a server is started by running
```
python src/run_server.py --protocol grpc --host 10.250.231.222 --port 9001 --node-id node1 --db-path ./data/node1.db 
```
where node-id specifies a unique ID of the server and db-path gives the path to this servers database for persistent storage.


When running more than one server, additional servers need to specify the addresses of the servers already in the system that they want to connect to. They do this with those nodes' node_ids and addresses:
```
python src/run_server.py --protocol grpc --host 10.250.231.222 --port 9002 --node-id node2 --db-path ./data/node2.db --peer node1:10.250.231.222:9001 
```
```
python src/run_server.py --protocol grpc --host 10.250.121.174 --port 9003 --node-id node3 --db-path ./data/node3.db --peer node1:10.250.231.222:9001 --peer node2:10.250.231.222:9002
```
Note that only previously servers have to be specified as peers, but more peers can be specified (if one already knows which servers will start up later).


## Running Client and GUI
To run the client, as before, run
```
python src/run_gui.py 
```
or
```
python src/run_gui.py --server 192.168.12.183:9001
```
If no server flag is given, a random server is chosen. Else, the specified server is chosen.


# Notes to self - Ignore below





# Connect to Node 3 (on second machine)
python src/run_gui.py --server 192.168.12.202:9003


If we must update IP adresses:

- in aforementioned commands
- in hardcoded lists.




Node1
```
python3 src/run_server.py --node-id 1 --host 10.250.231.222 --port 9001 --db-path ./data/node1.db
```

```
python3 src/run_server.py --node-id 2 --host 10.250.231.222 --port 9002 --db-path ./data/node2.db
```

```
python3 src/run_server.py --node-id 3 --host 10.250.231.222 --port 9003 --db-path ./data/node3.db
```

```
python src/run_server.py --protocol grpc --host 10.250.231.222 --port 9001 --node-id node1 --db-path ./data/node1.db --peer node2:10.250.231.222:9002 --peer node3:10.250.121.174:9003
```

```
python src/run_server.py --protocol grpc --host 10.250.231.222 --port 9002 --node-id node2 --db-path ./data/node2.db --peer node1:10.250.231.222:9001 --peer node3:10.250.121.174:9003
```

```
python src/run_server.py --protocol grpc --host 10.250.121.174 --port 9003 --node-id node3 --db-path ./data/node3.db --peer node1:10.250.231.222:9001 --peer node2:10.250.231.222:9002
```

RUNNING GUI

python src/run_gui.py --server 10.250.231.222:9001

python src/run_gui.py --server 10.250.231.222:9002

python src/run_gui.py --server 10.250.121.174:9003





ULRIK TESTING (IGNORE BELOW HERE)

# Node 1
python src/run_server.py --protocol grpc --host 192.168.12.183 --port 9001 --node-id node1 --db-path ./data/node1.db --peer node2:192.168.12.183:9002 --peer node3:192.168.12.202:9003

# Node 2
python src/run_server.py --protocol grpc --host 192.168.12.183 --port 9002 --node-id node2 --db-path ./data/node2.db --peer node1:192.168.12.183:9001 --peer node3:192.168.12.202:9003

# Node 3
python src/run_server.py --protocol grpc --host 192.168.12.202 --port 9003 --node-id node3 --db-path ./data/node3.db --peer node1:192.168.12.183:9001 --peer node2:192.168.12.183:9002



RUN GUI

# Connect to Node 1 or 2 (both on first machine)
python src/run_gui.py --server 192.168.12.183:9001
# or
python src/run_gui.py --server 192.168.12.183:9002

# Connect to Node 3 (on second machine)
python src/run_gui.py --server 192.168.12.202:9003


If we must update IP adresses:

- in aforementioned commands
- in hardcoded lists.




```
python src/run_server.py --protocol grpc --host 10.250.231.222 --port 9001 --node-id node1 --db-path ./data/node1.db
```

```
python src/run_server.py --protocol grpc --host 10.250.231.222 --port 9002 --node-id node2 --db-path ./data/node2.db --peer node1:10.250.231.222:9001
```

```
python src/run_server.py --protocol grpc --host 10.250.121.174 --port 9003 --node-id node3 --db-path ./data/node3.db --peer node1:10.250.231.222:9001 --peer node2:10.250.231.222:9002
```
