from enum import Enum, auto, IntEnum

class Command(IntEnum):
    """Command codes for the custom protocol"""
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

