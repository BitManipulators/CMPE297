import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../models/conversation.dart';
import '../models/chat_message.dart';
import '../config/app_config.dart';

class ConversationService extends ChangeNotifier {
  static const String _baseUrl = AppConfig.backendBaseUrl;
  Conversation? _currentConversation;
  final List<Conversation> _conversations = [];

  Conversation? get currentConversation => _currentConversation;
  List<Conversation> get conversations => _conversations;

  Future<Conversation> createConversation({
    String? name,
    required String type, // "one_to_one" or "group"
    required List<String> participantIds,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/conversations'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'name': name,
          'type': type,
          'participantIds': participantIds,
        }),
      );

      if (response.statusCode == 200) {
        final conversationData = json.decode(response.body);
        final conversation = Conversation.fromJson(conversationData);
        _conversations.add(conversation);
        notifyListeners();
        return conversation;
      } else {
        throw Exception('Failed to create conversation: ${response.body}');
      }
    } catch (e) {
      debugPrint('Error creating conversation: $e');
      rethrow;
    }
  }

  Future<Conversation> getConversation(String conversationId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/conversations/$conversationId'),
      );

      if (response.statusCode == 200) {
        final conversationData = json.decode(response.body);
        return Conversation.fromJson(conversationData);
      } else {
        throw Exception('Failed to get conversation: ${response.body}');
      }
    } catch (e) {
      debugPrint('Error getting conversation: $e');
      rethrow;
    }
  }

  Future<List<ChatMessage>> getMessages(String conversationId, {int limit = 50}) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/conversations/$conversationId/messages?limit=$limit'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final messagesList = data['messages'] as List;
        return messagesList
            .map((msg) => ChatMessage.fromJson(msg, currentUserId: null))
            .toList()
            .reversed
            .toList(); // Reverse to show oldest first
      } else {
        throw Exception('Failed to get messages: ${response.body}');
      }
    } catch (e) {
      debugPrint('Error getting messages: $e');
      return [];
    }
  }

  Future<void> addBotToConversation(String conversationId) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/conversations/$conversationId/add-bot'),
      );

      if (response.statusCode == 200) {
        // Update local conversation
        final index = _conversations.indexWhere((c) => c.id == conversationId);
        if (index != -1) {
          final updated = Conversation(
            id: _conversations[index].id,
            name: _conversations[index].name,
            type: _conversations[index].type,
            participants: _conversations[index].participants,
            createdAt: _conversations[index].createdAt,
            hasBot: true,
          );
          _conversations[index] = updated;
          if (_currentConversation?.id == conversationId) {
            _currentConversation = updated;
          }
          notifyListeners();
        }
      }
    } catch (e) {
      debugPrint('Error adding bot to conversation: $e');
      rethrow;
    }
  }

  void setCurrentConversation(Conversation? conversation) {
    _currentConversation = conversation;
    notifyListeners();
  }

  void loadConversations(List<Conversation> conversations) {
    _conversations.clear();
    _conversations.addAll(conversations);
    notifyListeners();
  }
}

