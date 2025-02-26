### Problem description
Design exercise 1: Wire protocols
For this design exercise, you will be building a simple, client-server chat application. The application will allow users to send and receive text messages. There will be a centralized server that will mediate the passing of messages. The application should allow:
1: Creating an account. The user supplies a unique (login) name. If there is already an account with that name, the user is prompted for the password. If the name is not being used, the user is prompted to supply a password. The password should not be passed as plaintext.
2: Log in to an account. Using a login name and password, log into an account. An incorrect login or bad user name should display an error. A successful login should display the number of unread messages.
3: List accounts, or a subset of accounts that fit a text wildcard pattern. If there are more accounts than can comfortably be displayed, allow iterating through the accounts.
4. Send a message to a recipient. If the recipient is logged in, deliver immediately; if not the message should be stored until the recipient logs in and requests to see the message.
5: Read messages. If there are undelivered messages, display those messages. The user should be able to specify the number of messages they want delivered at any single time.
6. Delete a message or set of messages. Once deleted messages are gone.
7. Delete an account. You will need to specify the semantics of deleting an account that contains unread messages.
The client should offer a reasonable graphical interface. Connection information may be specified as either a command-line option or in a configuration file.
You will need to design the wire protocol— what information is sent over the wire. Communication should be done using sockets constructed between the client and server. It should be possible to have multiple clients connected at any time. Design your implementation using some care; there will be other assignments that will utilize this codebase.
You should build two implementations— one should use a custom wire protocol; you should strive to make this protocol as efficient as possible. The other should use JSON. You should then measure the size of the information passed between the client and the server, writing up a comparison in your engineering notebook, along with some remarks on what the difference makes to the efficiency and scalability of the service.
Implementations will be demonstrated to other members of the class on 2/10, where you will also undergo a code review of your code and give a code review of someone else. The code review should include evaluations of the test code coverage and documentation of the system. Code reviews, including a grade, will be turned in on Canvas, along with your engineering notebook and a link to your code repo.

Questions
	- Okay to have a separate login and create account? More clean in my view.
	- Iterating through accounts when searching - is scrolling okay?
	- Do you want to track "online users" by the way you phrase deliver immediately? Or is it okay to just see all messages in general. I don't understand the distinction between being online or not.


Design choices
	- We decided to keep the login and create account as two different sections for security reasons. This is something used in most web applications as well - you get prompted to either create an account or log in, and get sent to different input fields.


Plan
Phase 1 - Foundation 
	• Set up basic client-server architecture
	• Design wire protocol formats (both custom and JSON)
	• Create test infrastructure
	• Implement basic connection handling
Phase 2 - Authentication 
	• Implement account creation
	• Implement login system
	• Design password hashing mechanism
	• Add basic tests for authentication
Phase 3 - Core Messaging 
	• Implement basic message sending/receiving
	• Add message storage on server
	• Implement immediate delivery for online users
	• Add message queuing for offline users
Phase 4 - Account Management 
	• Implement account listing
	• Add wildcard search
	• Implement pagination for account lists
	• Add account deletion logic
Phase 5 - Message Management 
	• Implement message reading with pagination
	• Add message deletion
	• Handle unread message counts
	• Add tests for message operations
Phase 6 - GUI Development 
	• Design basic GUI layout
	• Implement GUI components
	• Connect GUI to client logic
	• Add error handling and user feedback
Phase 7 - Protocol Comparison 
	• Implement JSON version
	• Add measurement tools
	• Compare protocols
	• Document findings
Phase 8 - Final Polish 
	• Complete documentation
	• Finish test coverage
	• Prepare for code review
	• Final bug fixes


Custom socket format
Example of message format:
[1 byte version][1 byte Command][2 bytes Length][Payload]

We have the following command encoding:
    ERROR = 0
    CREATE_ACCOUNT = 1
    AUTH = 2
    LIST_ACCOUNTS = 3
    SEND_MESSAGE = 4
    GET_MESSAGES = 5
    MARK_READ = 6
    DELETE_MESSAGES = 7
    DELETE_ACCOUNT = 8
    GET_UNREAD_COUNT = 9

For instance authentication
0x01 [Length] [username_length(1)][username][password_hash(32)]
And message sending
0x03 [Length] [recipient_length(1)][recipient][message_length(2)][message]


JSON Protocol Message format
The key differences between this and our custom protocol are:
	• Human Readable: JSON format is human-readable and easier to debug
	• Self-Describing: Each field is explicitly named
	• Flexible: Easy to add new fields without breaking compatibility
	• Larger Size: Messages will be larger due to field names and text encoding
	• Standard Format: Better tooling support and easier integration
The tradeoff is primarily in message size and parsing overhead. For example:
	• Custom protocol "auth" message might be ~40 bytes
	• JSON "auth" message might be ~100 bytes or more


Making test_protocols.py, which creates some test cases, and encodes both in JSON and our custom courses. Then we compare both it times it takes to encode, in addition to the size of the string and convert that to bytes. We observe that the custom format is much cheaper in both metrics.

Hashing for passwords
When making a hash function for the password, we also need a salt, that together with the password string maps to one value.

Unit testing
unittest.main(verbosity=2) runs all test cases in a Python script using the unittest framework. The verbosity=2argument increases the level of detail in the output, displaying each test method name along with its result (e.g., ok, FAIL, or ERROR). This makes debugging easier by providing more granular feedback on which tests passed or failed, rather than just a summary. The unittest.main() function automatically discovers and runs all test methods in the script that follow the test_* naming convention.

We follow the TDD (test driven development) approach, to ensure everything works along the way.


Listing accounts
Here, we take in the following Args:
            pattern: Wildcard pattern to match usernames against
            page: Page number (1-based)
            page_size: Number of accounts per page

We use this for pageination, in case we have a lot of users matching the pattern.


TESTED:
Opening on a client side from external terminal. Created account, logged into that account, successful and failed login dependent on password, listing account when searching for the name exactly.


Message functionality
We build according to the building tests and then developing. We first build the JSON one, as it is easier to debug, test it, before we make the custom one.



Tests
In the tests, we care about functionality tests, and not checking specs on the protocols, as this can change for later version numbers. We split the unit test into parts: a protocol test and a integration test. The first one is only checking that the 

Added a version number to the wire protocol.


Comparison test of protocols
We test the following tests.
AUTH Message
{
    "username": "testuser123",
    "password_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  // 32-byte hash
}
SEND_MESSAGE
{
    "recipient": "user456",
    "message": "Hello, this is a test message that's relatively long to simulate real-world usage!",
    "timestamp": "2024-02-01T12:34:56Z"
}
LIST_ACCOUNT
{
    "pattern": "test*",
    "page": 1,
    "page_size": 20
}


Long messages: Double click on the message in the GUI, and it will show the full message in a popup.



Compare encoding performance between protocols ... 
Encoding Performance Test (10,000 iterations):
------------------------------------------------------------
AUTH:
  Custom: 0.0028 seconds
  JSON:   0.0184 seconds
  Ratio:  6.61x slower
SEND_MESSAGE:
  Custom: 0.0024 seconds
  JSON:   0.0184 seconds
  Ratio:  7.60x slower
LIST_ACCOUNTS:
  Custom: 0.0023 seconds
  JSON:   0.0162 seconds
  Ratio:  7.01x slower
ok
test_message_sizes (__main__.ProtocolComparisonTests.test_message_sizes)
Compare message sizes between protocols ... 
Message Size Comparison:
------------------------------------------------------------
Message Type         Custom (bytes)  JSON (bytes)    Ratio     
------------------------------------------------------------
AUTH                 48              126             2.62x
SEND_MESSAGE         96              212             2.21x
LIST_ACCOUNTS        52              103             1.98x
ok

----------------------------------------------------------------------
Ran 2 tests in 0.061s
