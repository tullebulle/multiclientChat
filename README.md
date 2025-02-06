# multiclientChat


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