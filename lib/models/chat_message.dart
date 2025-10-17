import 'package:json_annotation/json_annotation.dart';
import 'package:dash_chat_2/dash_chat_2.dart';

part 'chat_message.g.dart';

@JsonSerializable()
class ChatMessage {
  final String id;
  final String text;
  final DateTime createdAt;
  final bool isUser;
  final String? imageUrl;
  final MessageType type;

  ChatMessage({
    required this.id,
    required this.text,
    required this.createdAt,
    required this.isUser,
    this.imageUrl,
    this.type = MessageType.text,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) =>
      _$ChatMessageFromJson(json);

  Map<String, dynamic> toJson() => _$ChatMessageToJson(this);

  ChatMessage toDashChatMessage() {
    return ChatMessage(
      id: id,
      text: text,
      createdAt: createdAt,
      isUser: isUser,
    );
  }
}

enum MessageType {
  text,
  image,
  voice,
}