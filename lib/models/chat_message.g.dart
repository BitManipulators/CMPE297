// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'chat_message.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ChatMessage _$ChatMessageFromJson(Map<String, dynamic> json) => ChatMessage(
  id: json['id'] as String,
  text: json['text'] as String,
  createdAt: DateTime.parse(json['createdAt'] as String),
  isUser: json['isUser'] as bool,
  imageUrl: json['imageUrl'] as String?,
  type:
      $enumDecodeNullable(_$MessageTypeEnumMap, json['type']) ??
      MessageType.text,
  userId: json['userId'] as String?,
  userName: json['userName'] as String?,
  conversationId: json['conversationId'] as String?,
  isBot: json['isBot'] as bool? ?? false,
  clientMessageId: json['clientMessageId'] as String?,
);

Map<String, dynamic> _$ChatMessageToJson(ChatMessage instance) =>
    <String, dynamic>{
      'id': instance.id,
      'text': instance.text,
      'createdAt': instance.createdAt.toIso8601String(),
      'isUser': instance.isUser,
      'imageUrl': instance.imageUrl,
      'type': _$MessageTypeEnumMap[instance.type]!,
      'userId': instance.userId,
      'userName': instance.userName,
      'conversationId': instance.conversationId,
      'isBot': instance.isBot,
      'clientMessageId': instance.clientMessageId,
    };

const _$MessageTypeEnumMap = {
  MessageType.text: 'text',
  MessageType.image: 'image',
  MessageType.voice: 'voice',
};
