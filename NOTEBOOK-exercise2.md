# Engineering notebook for implementing the gRPC protocol

### Questions: 
Re-implement the chat application you built for the first design exercise, but replace using sockets and a custom wire protocol/JSON with gRPC or some similar RPC package. Does the use of this tool make the application easier or more difficult? What does it do to the size of the data passed? How does it change the structure of the client? The server? How does this change the testing of the application?

###  Does it make the application easier or more difficult?
Easier! A lot of the things we had to write explicit code for in our socket implementation now has already been done for us. We specify which communication we want to have over the channel in the .proto file and then the code for sending and receiving messages as well as decoding and encoding them into bytes is auto-generated by the GRPC package. 

### What does it do to the size of the data passed?
Here is our benchmark for three representative operations:

| Message Type | Custom (bytes) | JSON (bytes) | gRPC (bytes) | JSON/Custom | gRPC/Custom |
|-------------|---------------|--------------|--------------|-------------|-------------|
| AUTH | 49 | 126 | 47 | 2.57x | 0.96x |
| SEND_MESSAGE | 96 | 175 | 93 | 1.82x | 0.97x |
| LIST_ACCOUNTS | 10 | 75 | 7 | 7.50x | 0.70x |
| DELETE_MESSAGES | 30 | 104 | 12 | 3.47x | 0.40x |

The reason that gRPC is using less bytes than the custom protocol is that gRPC uses variable-length integers, so -- for example -- in the case of DELETE_MESSAGES, in the benchmark above, the message IDs sent are all fairly small numbers, so gRPC uses less bytes by encoding them in less than 4 bytes (as our protocol does). See https://protobuf.dev/programming-guides/encoding/

If, instead, we run DELETE_MESSAGES with the same number of messages (6) as in the benchmark above, but use large message IDs (that require 4 bytes to be encoded), we get that our protocol is slightly more efficient:

| Message Type | Custom (bytes) | JSON (bytes) | gRPC (bytes) | JSON/Custom | gRPC/Custom |
|-------------|---------------|--------------|--------------|-------------|-------------|
| DELETE_MESSAGES | 30 | 146 | 32 | 4.87x | 1.07x |

### How does it change the structure of the client?
- In short, the structure of the client side changed minimally on a high level. It changed in regards to how messages are encoded and sent.
- Just like with the other two message protocols, we created a new, protocol specific client file handling communication from the client to the server. For all the operations we want to implement, there is a function that is being called by the (non-protocol specific) GUI. These functions create the corresponding GRPC Request object, call the GRPC, and handle the response. Compared to the custom and JSON protocol, the code for encoding the payload into a bitstring, sending it to the server, and decoding the response didn't need to be written by us. Instead, we wrote the .proto specification of our GRPCs and the auto-generated code by the grpc package handles the encoding, sending, and decoding of messages. 

### How does it change the structure of the server?
- First, we needed to adapt the run_server file. Since we now use a grpc server, we no longer use sockets. We use the concurrent package with the threading package to handle multiple client connections at once. We chose to set the maximum number of simultaneously acive workers to be 10 -- after all we are CS students so its unlikely that our number of friends using this service would ever exceed 10.
- For the server file handling incoming communication, we had to write a GRPC-specific file defining methods for handling all our GRPC calls. The simplest way to make this work would have been to have this GRPC server class use our server base from the other two protocols, but we realized that our server base implementation from the first exercise wasn't doing a great job at passing error messages (since they weren't accounted for in our custom protocol for space reasons), so we decided to re-write our server code specifically for the GRPC protocol -- in which we were more careful to allow for richer error message passing -- in the GRPC server class. Other than this,similarly to the client side, we no longer needed the code for receiving a message, decoding it, encoding a response and returning it, since the auto-generated GRPC code based on our .proto file handles this for us.

### How does this change the testing of the application?
- First, the test cases for the encoding, decoding, and the methods on the client side got a lot simpler. To test these methods, we made testcases for each method, testing both success and failure. However, now we don't need to specifically test our custom encode/decode functions but just assert the correct GRPC request/response objects are being sent and received and that they contain the right information. The server-side tests function similarly.
- On top of the expected errors we were already testing for, we added test cases for different grpc-specific errors that may occur to ensure that both client and server side handle those correctly.
    - We test the handling of GRPC network errors received by the client side.
    - We added more test cases for data locking on the server side, so no data corruption/races occur when multiple threads/clients try to make changes simultaneously.








