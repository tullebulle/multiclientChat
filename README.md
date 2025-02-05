# multiclientChat


#### Custom Protocol
To run the server with the custom protocol, use the following command:

```bash
python chat_app/run_server.py --protocol custom
```

To run a client gui, use the following command:

```bash
python chat_app/run_gui.py --protocol custom
```

To unit test the custom protocol, use the following command:

```bash
python -m chat_app.custom_protocol.tests.test_protocol
```

To run the integration tests, use the following command:

```bash
python -m chat_app.custom_protocol.tests.test_integration
```

#### JSON Protocol

likewise, to run a client gui with the JSON protocol, use the following command:


To run the server with the JSON protocol, use the following command:

```bash
python chat_app/run_server.py --protocol json
```
and run the gui client with the JSON protocol, use the following command:
```bash
python chat_app/run_gui.py --protocol json
```



