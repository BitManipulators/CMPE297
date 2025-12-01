import 'dart:async';
import 'dart:convert';
import 'package:into_the_wild/models/user.dart';
import 'package:into_the_wild/models/conversation.dart';
import 'package:into_the_wild/models/chat_message.dart';

/// Mock backend server for integration tests
/// Simulates HTTP API and WebSocket responses
class MockBackend {
  final Map<String, User> _users = {};
  final Map<String, Conversation> _conversations = {};
  final Map<String, List<ChatMessage>> _messages = {};
  final Map<String, StreamController<String>> _webSocketControllers = {};
  
  int _nextUserId = 1;
  int _nextConversationId = 1;
  int _nextMessageId = 1;

  /// Register a new user
  User registerUser(String username, {String? email}) {
    final userId = 'user_$_nextUserId';
    _nextUserId++;
    
    final user = User(
      id: userId,
      username: username,
      email: email,
      createdAt: DateTime.now().toIso8601String(),
    );
    
    _users[userId] = user;
    return user;
  }

  /// Get user by ID
  User? getUser(String userId) {
    return _users[userId];
  }

  /// Create a conversation
  Conversation createConversation({
    required String type,
    required List<String> participantIds,
    String? name,
  }) {
    final conversationId = 'conv_$_nextConversationId';
    _nextConversationId++;
    
    final conversation = Conversation(
      id: conversationId,
      name: name ?? 'Test Conversation',
      type: type,
      participantIds: participantIds,
      createdAt: DateTime.now(),
    );
    
    _conversations[conversationId] = conversation;
    _messages[conversationId] = [];
    
    return conversation;
  }

  /// Get conversation by ID
  Conversation? getConversation(String conversationId) {
    return _conversations[conversationId];
  }

  /// Get all conversations for a user
  List<Conversation> getUserConversations(String userId) {
    return _conversations.values
        .where((conv) => conv.participants.contains(userId))
        .toList();
  }

  /// Add a message to a conversation
  ChatMessage addMessage({
    required String conversationId,
    required String senderId,
    required String text,
    String? imageUrl,
    String? clientMessageId,
  }) {
    final messageId = 'msg_$_nextMessageId';
    _nextMessageId++;
    
    final user = _users[senderId];
    if (user == null) {
      throw Exception('User not found: $senderId');
    }
    
    final message = ChatMessage(
      id: messageId,
      conversationId: conversationId,
      userId: senderId,
      userName: user.username,
      text: text,
      imageUrl: imageUrl,
      createdAt: DateTime.now(),
      isUser: true,
      clientMessageId: clientMessageId,
    );
    
    _messages[conversationId]?.add(message);
    
    // Broadcast to all WebSocket listeners
    _broadcastMessage(conversationId, message);
    
    return message;
  }

  /// Get messages for a conversation
  List<ChatMessage> getMessages(String conversationId) {
    return _messages[conversationId] ?? [];
  }

  /// Create a WebSocket controller for a user
  StreamController<String> createWebSocketController(String userId) {
    final controller = StreamController<String>.broadcast();
    _webSocketControllers[userId] = controller;
    return controller;
  }

  /// Get WebSocket controller for a user
  StreamController<String>? getWebSocketController(String userId) {
    return _webSocketControllers[userId];
  }

  /// Broadcast a message to all participants in a conversation
  void _broadcastMessage(String conversationId, ChatMessage message) {
    final conversation = _conversations[conversationId];
    if (conversation == null) return;
    
    final messageData = {
      'type': 'new_message',
      'message': message.toJson(),
    };
    
    for (final participantId in conversation.participants) {
      final controller = _webSocketControllers[participantId];
      controller?.add(json.encode(messageData));
    }
  }

  /// Simulate WebSocket message handling
  void handleWebSocketMessage(String userId, Map<String, dynamic> data) {
    final type = data['type'];
    
    switch (type) {
      case 'send_message':
        addMessage(
          conversationId: data['conversationId'],
          senderId: userId,
          text: data['text'],
          clientMessageId: data['clientMessageId'],
        );
        break;
      case 'send_image':
        addMessage(
          conversationId: data['conversationId'],
          senderId: userId,
          text: data['text'] ?? '',
          imageUrl: 'data:${data['imageMimeType']};base64,${data['imageBase64']}',
          clientMessageId: data['clientMessageId'],
        );
        break;
      case 'join_conversation':
        // Send conversation history
        final conversationId = data['conversationId'];
        final messages = getMessages(conversationId);
        final controller = _webSocketControllers[userId];
        
        for (final message in messages) {
          controller?.add(json.encode({
            'type': 'new_message',
            'message': message.toJson(),
          }));
        }
        break;
      case 'get_all_groups':
        final conversations = getUserConversations(userId);
        final controller = _webSocketControllers[userId];
        
        controller?.add(json.encode({
          'type': 'all_groups',
          'conversations': conversations.map((c) => c.toJson()).toList(),
        }));
        break;
    }
  }

  /// Clean up all data
  void clear() {
    _users.clear();
    _conversations.clear();
    _messages.clear();
    
    for (final controller in _webSocketControllers.values) {
      controller.close();
    }
    _webSocketControllers.clear();
    
    _nextUserId = 1;
    _nextConversationId = 1;
    _nextMessageId = 1;
  }

  /// Close all WebSocket connections
  Future<void> dispose() async {
    for (final controller in _webSocketControllers.values) {
      await controller.close();
    }
    _webSocketControllers.clear();
  }
}
