import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/chat_message.dart';
import '../config/app_config.dart';

class WebSocketService extends ChangeNotifier {
  static String get _baseUrl => AppConfig.websocketBaseUrl;
  WebSocketChannel? _channel;
  String? _userId;
  bool _isConnected = false;
  StreamController<Map<String, dynamic>>? _messageController;
  StreamSubscription<dynamic>? _streamSubscription;
  Future<void>? _connectingFuture; // Lock to prevent concurrent connections


  Timer? _pingTimer;
  DateTime? _lastPongReceived;
  static const Duration _pingInterval = Duration(seconds: 30);
  static const Duration _pongTimeout = Duration(seconds: 10);

  bool get isConnected => _isConnected;
  Stream<Map<String, dynamic>>? get messageStream => _messageController?.stream;

  Future<void> connect(String userId) async {
    if (_isConnected && _userId == userId) {
      debugPrint('WebSocket already connected for user: $userId');
      return; // Already connected
    }

    // If a connection is already in progress, wait for it to complete
    if (_connectingFuture != null) {
      debugPrint('Connection already in progress, waiting...');
      await _connectingFuture;
      // After waiting, check if we're now connected to the right user
      if (_isConnected && _userId == userId) {
        return;
      }
    }

    // Create a new connection future and store it as the lock
    _connectingFuture = _performConnection(userId);
    try {
      await _connectingFuture;
    } finally {
      _connectingFuture = null;
    }
  }

  Future<void> _performConnection(String userId) async {
    try {
      // Properly clean up existing connection BEFORE creating a new one
      // Cancel subscription first
      await _streamSubscription?.cancel();
      _streamSubscription = null;

      // Close old channel if it exists
      if (_channel != null) {
        try {
          await _channel!.sink.close();
        } catch (e) {
          debugPrint('Error closing old channel: $e');
        }
        _channel = null;
      }

      // Close old message controller if it exists
      if (_messageController != null) {
        try {
          await _messageController!.close();
        } catch (e) {
          debugPrint('Error closing old message controller: $e');
        }
        _messageController = null;
      }

      _userId = userId;
      _messageController = StreamController<Map<String, dynamic>>.broadcast();

      final uri = Uri.parse('$_baseUrl/ws/$userId');
      debugPrint('Connecting to WebSocket: $uri');
      _channel = WebSocketChannel.connect(uri);

      // Wait a bit to ensure connection is established
      await Future.delayed(const Duration(milliseconds: 100));

     _isConnected = true;
      _lastPongReceived = DateTime.now();
      notifyListeners();
      debugPrint('WebSocket connected successfully for user: $userId');

      // Start ping monitoring
      _startPingMonitoring();

      // Listen for messages
      _streamSubscription = _channel!.stream.listen(
        (message) {
          try {
            final data = json.decode(message);
            final messageType = data['type'] as String?;

            debugPrint('WebSocket message received: $messageType');

            // Handle ping from server - send pong back
            if (messageType == 'ping') {
              _sendPong();
              return;
            }

            // Handle pong from server (if you implement client-side ping)
            if (messageType == 'pong') {
              _lastPongReceived = DateTime.now();
              debugPrint('Pong received from server');
              return;
            }

            // Handle pong_ack from server (acknowledgment that server received our pong)
            if (messageType == 'pong_ack') {
              _lastPongReceived = DateTime.now();
              debugPrint('Pong acknowledgment received from server');
              return;
            }

            _messageController?.add(data);
          } catch (e) {
            debugPrint('Error parsing WebSocket message: $e');
            debugPrint('Raw message: $message');
          }
        },
        onError: (error) {
          debugPrint('WebSocket stream error: $error');
          _stopPingMonitoring();
          _isConnected = false;
          notifyListeners();
        },
        onDone: () {
          debugPrint('WebSocket connection closed');
          _stopPingMonitoring();
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

  void _startPingMonitoring() {
    _stopPingMonitoring(); // Clear any existing timer

    _pingTimer = Timer.periodic(_pingInterval, (timer) {
      if (!_isConnected) {
        timer.cancel();
        return;
      }

      // Check if we've received a pong recently
      if (_lastPongReceived != null) {
        final timeSinceLastPong = DateTime.now().difference(_lastPongReceived!);
        if (timeSinceLastPong > _pongTimeout + _pingInterval) {
          debugPrint('No pong received for ${timeSinceLastPong.inSeconds}s - connection may be dead');
          // Optionally reconnect here
          _handleDeadConnection();
          return;
        }
      }
    });
  }

  void _stopPingMonitoring() {
    _pingTimer?.cancel();
    _pingTimer = null;
  }

  void _sendPong() {
    if (!_isConnected || _channel == null) {
      return;
    }

    try {
      final message = {
        'type': 'pong',
        'timestamp': DateTime.now().toIso8601String(),
      };
      _channel!.sink.add(json.encode(message));
      debugPrint('Pong sent to server');
    } catch (e) {
      debugPrint('Error sending pong: $e');
    }
  }

  void _sendPing() {
    if (!_isConnected || _channel == null) {
      return;
    }

    try {
      final message = {
        'type': 'ping',
        'timestamp': DateTime.now().toIso8601String(),
      };
      _channel!.sink.add(json.encode(message));
      debugPrint('Ping sent to server');
    } catch (e) {
      debugPrint('Error sending ping: $e');
    }
  }

  void _handleDeadConnection() {
    debugPrint('Handling dead connection - attempting reconnect');
    final currentUserId = _userId;
    disconnect();

    // Optionally auto-reconnect
    if (currentUserId != null) {
      Future.delayed(const Duration(seconds: 2), () {
        connect(currentUserId);
      });
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
    _lastPongReceived = null;
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

  void sendImageMessage({
    String? imageUrl,
    String? imageBase64,
    String? imageMimeType,
    required String conversationId,
    required String userName,
    required String userId,
    String text = "",
    String? clientMessageId,
  }) {
    if (!_isConnected || _channel == null) {
      debugPrint('WebSocket not connected. isConnected: $_isConnected, channel: ${_channel != null}');
      throw Exception('WebSocket not connected');
    }

    // Prefer imageUrl (Firebase Storage URL) over base64
    final message = {
      'type': 'send_image',
      'conversationId': conversationId,
      'userName': userName,
      'userId': userId,
      'text': text,
    };

    if (imageUrl != null) {
      // Send Firebase Storage URL (preferred)
      message['imageUrl'] = imageUrl;
    } else if (imageBase64 != null && imageMimeType != null) {
      // Fallback: send base64 if URL not available
      message['imageBase64'] = imageBase64;
      message['imageMimeType'] = imageMimeType;
    } else {
      throw Exception('Either imageUrl or imageBase64 with imageMimeType must be provided');
    }

    if (clientMessageId != null) {
      message['clientMessageId'] = clientMessageId;
    }

    try {
      _channel!.sink.add(json.encode(message));
      debugPrint('Image message sent via WebSocket (${imageUrl != null ? "URL" : "base64"})');
    } catch (e) {
      debugPrint('Error sending image message via WebSocket: $e');
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

  void requestAllGroups() {
    if (!_isConnected || _channel == null) {
      throw Exception('WebSocket not connected');
    }

    final message = {
      'type': 'get_all_groups',
    };

    _channel!.sink.add(json.encode(message));
  }

  @override
  void dispose() {
    disconnect();
    super.dispose();
  }
}

