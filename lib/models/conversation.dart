import 'package:json_annotation/json_annotation.dart';

part 'conversation.g.dart';

@JsonSerializable()
class Conversation {
  final String id;
  final String? name;
  final String type; // "one_to_one" or "group"
  final List<String> participants;
  final String createdAt;
  final bool hasBot;

  Conversation({
    required this.id,
    this.name,
    required this.type,
    required this.participants,
    required this.createdAt,
    this.hasBot = false,
  });

  factory Conversation.fromJson(Map<String, dynamic> json) =>
      _$ConversationFromJson(json);

  Map<String, dynamic> toJson() => _$ConversationToJson(this);
}

