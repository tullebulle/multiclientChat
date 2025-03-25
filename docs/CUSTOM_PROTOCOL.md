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
    - CREATE_ACCOUNT:       [1 byte username length][username][1 byte password_hash_length:1][password_hash]
    - AUTH:                 [1 byte username length][username][1 byte password_hash_length:1][password_hash]
    - LIST_ACCOUNTS:        [1 byte pattern length][pattern]
    - SEND_MESSAGE:         [1 byte recipient length][recipient][2 byte content_length][content]
    - GET_MESSAGES:         [1 byte include_read]
    - MARK_READ:            [2 byte messages count][4 byte message_id]...[4 byte message_id]
    - DELETE_MESSAGES:      [2 byte messages count][4 byte message_id]...[4 byte message_id]
    - DELETE_ACCOUNT:       [1 byte username length][username][1 byte password_hash_length:1][password_hash]
    - GET_UNREAD_COUNT:     None

Server response:
    - CREATE_ACCOUNT:       [1 byte success]
    - AUTH:                 [1 byte success]
    - LIST_ACCOUNTS:        [1 byte matching_accounts length][1 byte username length][username]...[1 byte username length][username]
    - SEND_MESSAGE:         [4 byte message_id]
    - GET_MESSAGES:         [2 byte messages count][4 byte message_id][1 byte sender length][sender][2 byte content length][content][8 byte timestamp][1 byte is_read]...[4 byte message_id][1 byte sender length][sender][2 byte content length][content][8 byte timestamp][1 byte is_read]
    - MARK_READ:            [2 byte count]
    - DELETE_MESSAGES:      [2 byte count]
    - DELETE_ACCOUNT:       [1 byte success]
    - GET_UNREAD_COUNT:     [2 byte count]







