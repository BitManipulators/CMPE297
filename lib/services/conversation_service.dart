import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import '../models/conversation.dart';
import '../models/chat_message.dart';
import '../config/app_config.dart';
import 'analytics_service.dart';

class ConversationService extends ChangeNotifier {
  static String get _baseUrl => AppConfig.backendBaseUrl;
  Conversation? _currentConversation;
  final List<Conversation> _conversations = [];
  final Map<String, String> _usernameCache = {}; // Cache for participant usernames

  Conversation? get currentConversation => _currentConversation;
  List<Conversation> get conversations => _conversations;
  Map<String, String> get usernameCache => _usernameCache;

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

        // Check if conversation already exists in list
        final exists = _conversations.any((c) => c.id == conversation.id);
        if (!exists) {
          _conversations.add(conversation);
        } else {
          // Update existing conversation
          final index = _conversations.indexWhere((c) => c.id == conversation.id);
          _conversations[index] = conversation;
        }

        // Log analytics event
        await AnalyticsService.logConversationCreated(conversationType: type);

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
        final messages = messagesList
            .map((msg) => ChatMessage.fromJson(msg, currentUserId: null))
            .toList()
            .reversed
            .toList(); // Reverse to show oldest first

        // Cache usernames from messages
        for (final message in messages) {
          if (message.userId != null && message.userName != null) {
            updateUsernameCache(message.userId!, message.userName!);
          }
        }

        return messages;
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

  Future<void> removeBotFromConversation(String conversationId) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/conversations/$conversationId/remove-bot'),
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
            hasBot: false,
          );
          _conversations[index] = updated;
          if (_currentConversation?.id == conversationId) {
            _currentConversation = updated;
          }
          notifyListeners();
        }
      }
    } catch (e) {
      debugPrint('Error removing bot from conversation: $e');
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

  Future<List<Conversation>> getAllConversations(String userId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/conversations?user_id=$userId'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final conversationsList = data['conversations'] as List;
        final conversations = conversationsList
            .map((conv) => Conversation.fromJson(conv))
            .toList();

        // Update local list
        _conversations.clear();
        _conversations.addAll(conversations);
        notifyListeners();

        return conversations;
      } else {
        throw Exception('Failed to get conversations: ${response.body}');
      }
    } catch (e) {
      debugPrint('Error getting all conversations: $e');
      return [];
    }
  }

  Future<Conversation> joinGroup(String conversationId, String userId) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/conversations/$conversationId/join'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'user_id': userId}),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final conversation = Conversation.fromJson(data['conversation']);

        // Update local list
        final index = _conversations.indexWhere((c) => c.id == conversationId);
        if (index != -1) {
          _conversations[index] = conversation;
        } else {
          _conversations.add(conversation);
        }

        // Log analytics event
        await AnalyticsService.logGroupJoined();

        notifyListeners();
        return conversation;
      } else {
        throw Exception('Failed to join group: ${response.body}');
      }
    } catch (e) {
      debugPrint('Error joining group: $e');
      rethrow;
    }
  }

  Future<Conversation> leaveGroup(String conversationId, String userId) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/conversations/$conversationId/leave'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({'user_id': userId}),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        final conversation = Conversation.fromJson(data['conversation']);

        // Update local list
        final index = _conversations.indexWhere((c) => c.id == conversationId);
        if (index != -1) {
          _conversations[index] = conversation;
        }

        // Log analytics event
        await AnalyticsService.logGroupLeft();

        notifyListeners();
        return conversation;
      } else {
        throw Exception('Failed to leave group: ${response.body}');
      }
    } catch (e) {
      debugPrint('Error leaving group: $e');
      rethrow;
    }
  }

  void addOrUpdateConversation(Conversation conversation) {
    final index = _conversations.indexWhere((c) => c.id == conversation.id);
    if (index != -1) {
      _conversations[index] = conversation;
    } else {
      _conversations.add(conversation);
    }
    notifyListeners();
  }

  void updateUsernameCache(String userId, String username) {
    if (_usernameCache[userId] != username) {
      _usernameCache[userId] = username;
      notifyListeners();
    }
  }
}

