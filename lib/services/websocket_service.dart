import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/chat_message.dart';
import '../config/app_config.dart';

class WebSocketService extends ChangeNotifier {
  static const String _baseUrl = AppConfig.websocketBaseUrl;
  WebSocketChannel? _channel;
  String? _userId;
  bool _isConnected = false;
  StreamController<Map<String, dynamic>>? _messageController;
  StreamSubscription<dynamic>? _streamSubscription;

  bool get isConnected => _isConnected;
  Stream<Map<String, dynamic>>? get messageStream => _messageController?.stream;

  Future<void> connect(String userId) async {
    if (_isConnected && _userId == userId) {
      debugPrint('WebSocket already connected for user: $userId');
      return; // Already connected
    }

    try {
      // Disconnect existing connection if any
      if (_channel != null) {
        await disconnect();
      }

      _userId = userId;
      _messageController = StreamController<Map<String, dynamic>>.broadcast();

      final uri = Uri.parse('$_baseUrl/ws/$userId');
      debugPrint('Connecting to WebSocket: $uri');
      _channel = WebSocketChannel.connect(uri);

      // Wait a bit to ensure connection is established
      await Future.delayed(const Duration(milliseconds: 100));

      _isConnected = true;
      notifyListeners();
      debugPrint('WebSocket connected successfully for user: $userId');

      // Cancel any existing subscription before creating a new one
      await _streamSubscription?.cancel();

      // Listen for messages
      _streamSubscription = _channel!.stream.listen(
        (message) {
          try {
            final data = json.decode(message);
            debugPrint('WebSocket message received: ${data['type']}');
            _messageController?.add(data);
          } catch (e) {
            debugPrint('Error parsing WebSocket message: $e');
            debugPrint('Raw message: $message');
          }
        },
        onError: (error) {
          debugPrint('WebSocket stream error: $error');
          _isConnected = false;
          notifyListeners();
        },
        onDone: () {
          debugPrint('WebSocket connection closed');
          _isConnected = false;
          _streamSubscription = null;
          notifyListeners();
        },
      );
    } catch (e) {
      debugPrint('Error connecting to WebSocket: $e');
      _isConnected = false;
      _channel = null;
      _streamSubscription = null;
      notifyListeners();
      rethrow;
    }
  }

  Future<void> disconnect() async {
    await _streamSubscription?.cancel();
    _streamSubscription = null;
    await _channel?.sink.close();
    await _messageController?.close();
    _channel = null;
    _messageController = null;
    _isConnected = false;
    _userId = null;
    notifyListeners();
  }

  void sendMessage({
    required String text,
    required String conversationId,
    required String userName,
    required String userId,
    String? clientMessageId,
  }) {
    if (!_isConnected || _channel == null) {
      debugPrint('WebSocket not connected. isConnected: $_isConnected, channel: ${_channel != null}');
      throw Exception('WebSocket not connected');
    }

    final message = {
      'type': 'send_message',
      'text': text,
      'conversationId': conversationId,
      'userName': userName,
      'userId': userId,
    };

    if (clientMessageId != null) {
      message['clientMessageId'] = clientMessageId;
    }

    try {
      _channel!.sink.add(json.encode(message));
      debugPrint('Message sent via WebSocket: ${message['text']}');
    } catch (e) {
      debugPrint('Error sending message via WebSocket: $e');
      rethrow;
    }
  }

  void joinConversation(String conversationId) {
    if (!_isConnected || _channel == null) {
      throw Exception('WebSocket not connected');
    }

    final message = {
      'type': 'join_conversation',
      'conversationId': conversationId,
    };

    _channel!.sink.add(json.encode(message));
  }

  @override
  void dispose() {
    disconnect();
    super.dispose();
  }
}

