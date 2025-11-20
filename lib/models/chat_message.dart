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
  // Multi-user support fields
  final String? userId;
  final String? userName;
  final String? conversationId;
  final bool isBot;
  final String? clientMessageId; // Client-generated ID for matching optimistic messages

  ChatMessage({
    required this.id,
    required this.text,
    required this.createdAt,
    required this.isUser,
    this.imageUrl,
    this.type = MessageType.text,
    this.userId,
    this.userName,
    this.conversationId,
    this.isBot = false,
    this.clientMessageId,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json, {String? currentUserId}) {
    // Handle DateTime from ISO string, DateTime object, or number (timestamp)
    String createdAtString;
    if (json['createdAt'] is String) {
      createdAtString = json['createdAt'] as String;
    } else if (json['createdAt'] is DateTime) {
      createdAtString = (json['createdAt'] as DateTime).toIso8601String();
    } else if (json['createdAt'] is int) {
      // Handle Unix timestamp
      createdAtString = DateTime.fromMillisecondsSinceEpoch(json['createdAt'] as int).toIso8601String();
    } else {
      createdAtString = DateTime.now().toIso8601String();
    }

    // Handle isUser - derive from userId if not provided
    bool isUser = false;
    if (json['isUser'] != null) {
      isUser = json['isUser'] as bool;
    } else if (currentUserId != null && json['userId'] != null) {
      // Determine if message is from current user
      isUser = json['userId'] == currentUserId;
    }

    // Handle isBot - default to false if not provided
    bool isBot = json['isBot'] as bool? ?? false;

    // Create a modified json with all required fields
    final modifiedJson = Map<String, dynamic>.from(json);
    modifiedJson['createdAt'] = createdAtString;
    modifiedJson['isUser'] = isUser;
    modifiedJson['isBot'] = isBot;
    // clientMessageId is optional, so it's fine if it's not in json

    return _$ChatMessageFromJson(modifiedJson);
  }

  Map<String, dynamic> toJson() => _$ChatMessageToJson(this);

  ChatMessage toDashChatMessage() {
    return ChatMessage(
      id: id,
      text: text,
      createdAt: createdAt,
      isUser: isUser,
      userId: userId,
      userName: userName,
      conversationId: conversationId,
      isBot: isBot,
      clientMessageId: clientMessageId,
    );
  }
}

enum MessageType {
  text,
  image,
  voice,
}