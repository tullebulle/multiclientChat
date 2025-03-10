# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: src/grpc_protocol/chat.proto
# Protobuf Python Version: 4.25.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x1csrc/grpc_protocol/chat.proto\x12\x04\x63hat\"?\n\x14\x43reateAccountRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x15\n\rpassword_hash\x18\x02 \x01(\t\"?\n\x15\x43reateAccountResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x15\n\rerror_message\x18\x02 \x01(\t\"6\n\x0b\x41uthRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x15\n\rpassword_hash\x18\x02 \x01(\t\"6\n\x0c\x41uthResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x15\n\rerror_message\x18\x02 \x01(\t\"&\n\x13ListAccountsRequest\x12\x0f\n\x07pattern\x18\x01 \x01(\t\"@\n\x14ListAccountsResponse\x12\x11\n\tusernames\x18\x01 \x03(\t\x12\x15\n\rerror_message\x18\x02 \x01(\t\"?\n\x14\x44\x65leteAccountRequest\x12\x10\n\x08username\x18\x01 \x01(\t\x12\x15\n\rpassword_hash\x18\x02 \x01(\t\"?\n\x15\x44\x65leteAccountResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x15\n\rerror_message\x18\x02 \x01(\t\"m\n\x07Message\x12\n\n\x02id\x18\x01 \x01(\x05\x12\x0e\n\x06sender\x18\x02 \x01(\t\x12\x11\n\trecipient\x18\x03 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x04 \x01(\t\x12\x11\n\ttimestamp\x18\x05 \x01(\x03\x12\x0f\n\x07is_read\x18\x06 \x01(\x08\"8\n\x12SendMessageRequest\x12\x11\n\trecipient\x18\x01 \x01(\t\x12\x0f\n\x07\x63ontent\x18\x02 \x01(\t\"@\n\x13SendMessageResponse\x12\x12\n\nmessage_id\x18\x01 \x01(\r\x12\x15\n\rerror_message\x18\x02 \x01(\t\"*\n\x12GetMessagesRequest\x12\x14\n\x0cinclude_read\x18\x01 \x01(\x08\"M\n\x13GetMessagesResponse\x12\x1f\n\x08messages\x18\x01 \x03(\x0b\x32\r.chat.Message\x12\x15\n\rerror_message\x18\x02 \x01(\t\"&\n\x0fMarkReadRequest\x12\x13\n\x0bmessage_ids\x18\x01 \x03(\x05\":\n\x10MarkReadResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x15\n\rerror_message\x18\x02 \x01(\t\",\n\x15\x44\x65leteMessagesRequest\x12\x13\n\x0bmessage_ids\x18\x01 \x03(\x05\"@\n\x16\x44\x65leteMessagesResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x15\n\rerror_message\x18\x02 \x01(\t\"\x14\n\x12UnreadCountRequest\";\n\x13UnreadCountResponse\x12\r\n\x05\x63ount\x18\x01 \x01(\r\x12\x15\n\rerror_message\x18\x02 \x01(\t2\xf6\x04\n\x0b\x43hatService\x12H\n\rCreateAccount\x12\x1a.chat.CreateAccountRequest\x1a\x1b.chat.CreateAccountResponse\x12\x35\n\x0c\x41uthenticate\x12\x11.chat.AuthRequest\x1a\x12.chat.AuthResponse\x12\x45\n\x0cListAccounts\x12\x19.chat.ListAccountsRequest\x1a\x1a.chat.ListAccountsResponse\x12H\n\rDeleteAccount\x12\x1a.chat.DeleteAccountRequest\x1a\x1b.chat.DeleteAccountResponse\x12\x42\n\x0bSendMessage\x12\x18.chat.SendMessageRequest\x1a\x19.chat.SendMessageResponse\x12\x42\n\x0bGetMessages\x12\x18.chat.GetMessagesRequest\x1a\x19.chat.GetMessagesResponse\x12\x39\n\x08MarkRead\x12\x15.chat.MarkReadRequest\x1a\x16.chat.MarkReadResponse\x12K\n\x0e\x44\x65leteMessages\x12\x1b.chat.DeleteMessagesRequest\x1a\x1c.chat.DeleteMessagesResponse\x12\x45\n\x0eGetUnreadCount\x12\x18.chat.UnreadCountRequest\x1a\x19.chat.UnreadCountResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'src.grpc_protocol.chat_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_CREATEACCOUNTREQUEST']._serialized_start=38
  _globals['_CREATEACCOUNTREQUEST']._serialized_end=101
  _globals['_CREATEACCOUNTRESPONSE']._serialized_start=103
  _globals['_CREATEACCOUNTRESPONSE']._serialized_end=166
  _globals['_AUTHREQUEST']._serialized_start=168
  _globals['_AUTHREQUEST']._serialized_end=222
  _globals['_AUTHRESPONSE']._serialized_start=224
  _globals['_AUTHRESPONSE']._serialized_end=278
  _globals['_LISTACCOUNTSREQUEST']._serialized_start=280
  _globals['_LISTACCOUNTSREQUEST']._serialized_end=318
  _globals['_LISTACCOUNTSRESPONSE']._serialized_start=320
  _globals['_LISTACCOUNTSRESPONSE']._serialized_end=384
  _globals['_DELETEACCOUNTREQUEST']._serialized_start=386
  _globals['_DELETEACCOUNTREQUEST']._serialized_end=449
  _globals['_DELETEACCOUNTRESPONSE']._serialized_start=451
  _globals['_DELETEACCOUNTRESPONSE']._serialized_end=514
  _globals['_MESSAGE']._serialized_start=516
  _globals['_MESSAGE']._serialized_end=625
  _globals['_SENDMESSAGEREQUEST']._serialized_start=627
  _globals['_SENDMESSAGEREQUEST']._serialized_end=683
  _globals['_SENDMESSAGERESPONSE']._serialized_start=685
  _globals['_SENDMESSAGERESPONSE']._serialized_end=749
  _globals['_GETMESSAGESREQUEST']._serialized_start=751
  _globals['_GETMESSAGESREQUEST']._serialized_end=793
  _globals['_GETMESSAGESRESPONSE']._serialized_start=795
  _globals['_GETMESSAGESRESPONSE']._serialized_end=872
  _globals['_MARKREADREQUEST']._serialized_start=874
  _globals['_MARKREADREQUEST']._serialized_end=912
  _globals['_MARKREADRESPONSE']._serialized_start=914
  _globals['_MARKREADRESPONSE']._serialized_end=972
  _globals['_DELETEMESSAGESREQUEST']._serialized_start=974
  _globals['_DELETEMESSAGESREQUEST']._serialized_end=1018
  _globals['_DELETEMESSAGESRESPONSE']._serialized_start=1020
  _globals['_DELETEMESSAGESRESPONSE']._serialized_end=1084
  _globals['_UNREADCOUNTREQUEST']._serialized_start=1086
  _globals['_UNREADCOUNTREQUEST']._serialized_end=1106
  _globals['_UNREADCOUNTRESPONSE']._serialized_start=1108
  _globals['_UNREADCOUNTRESPONSE']._serialized_end=1167
  _globals['_CHATSERVICE']._serialized_start=1170
  _globals['_CHATSERVICE']._serialized_end=1800
# @@protoc_insertion_point(module_scope)
