The custom protocol is a binary protocol that is used to send messages between the server and the client.

The protocol follows the following format:
[1 byte Version][1 byte Command][2 bytes Length][Payload]

- Version is the version of the protocol, currently 0.
- Command is the command to be executed and determines the format of the payload. The command is encoded as an integer, as follows:
    - ERROR = 0
    - CREATE_ACCOUNT = 1
    - AUTH = 2
    - LIST_ACCOUNTS = 3
    - SEND_MESSAGE = 4
    - GET_MESSAGES = 5
    - MARK_READ = 6
    - DELETE_MESSAGES = 7
    - DELETE_ACCOUNT = 8
    - GET_UNREAD_COUNT = 9
- Length is the length of the payload.

Payload is the payload of the command. Its format depends on the command, and whether it is a client request or a server response. The strings are encoded as UTF-8.

Client request:
    - CREATE_ACCOUNT:       [1 byte username_length][username][1 byte password_hash_length:1][password_hash]
    - AUTH:                 [1 byte username_length][username][1 byte password_hash_length:1][password_hash]
    - SEND_MESSAGE:         [message_length(2)][message]
    - GET_MESSAGES:         [start_index(2)][end_index(2)]
    - MARK_READ:            [message_id(4)]
    - DELETE_MESSAGES:      [message_id(4)]
    - DELETE_ACCOUNT:       [username_length(1)][username]
    - GET_UNREAD_COUNT:     []
Server response:
    - ERROR:                [error_message_length(2)][error_message]
    - SUCCESS:              []








