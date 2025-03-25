
Starting a server


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
python src/run_server.py --protocol grpc --host 10.250.231.222 --port 9001 --node-id node1 --db-path ./data/node1 --peer node2:10.250.231.222:9002 --peer node3:10.250.121.174:9003
```

```
python src/run_server.py --protocol grpc --host 10.250.231.222 --port 9002 --node-id node2 --db-path ./data/node2 --peer node1:10.250.231.222:9001 --peer node3:10.250.121.174:9003
```



