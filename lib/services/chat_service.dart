import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:image_picker/image_picker.dart';
import '../models/chat_message.dart';
import '../models/conversation.dart';
import 'websocket_service.dart';
import 'conversation_service.dart';
import 'auth_service.dart';
import 'notification_service.dart';

class ChatService extends ChangeNotifier {
  final List<ChatMessage> _messages = [];
  final SpeechToText _speechToText = SpeechToText();
  final ImagePicker _imagePicker = ImagePicker();
  bool _isListening = false;
  bool _isLoading = false;
  String? _currentConversationId;
  bool _isLoadingConversation = false; // Flag to track if we're currently loading a conversation
  bool _conversationHistoryReceived = false; // Flag to track if conversation_history was received during loading

  // Services (injected via constructor or setter)
  WebSocketService? _webSocketService;
  ConversationService? _conversationService;
  AuthService? _authService;
  final NotificationService _notificationService = NotificationService();
  StreamSubscription<Map<String, dynamic>>? _messageSubscription;

  List<ChatMessage> get messages => _messages;
  bool get isListening => _isListening;
  bool get isLoading => _isLoading;
  String? get currentConversationId => _currentConversationId;

  ChatService() {
    _initializeSpeech();
  }

  // Initialize services
  void initializeServices({
    required WebSocketService webSocketService,
    required ConversationService conversationService,
    required AuthService authService,
  }) {
    _webSocketService = webSocketService;
    _conversationService = conversationService;
    _authService = authService;

    // Cancel any existing subscription before creating a new one
    _messageSubscription?.cancel();

    // Listen to WebSocket messages
    _messageSubscription = _webSocketService?.messageStream?.listen(_handleWebSocketMessage);
  }

  Future<void> _initializeSpeech() async {
    await _speechToText.initialize();
  }

  void _handleWebSocketMessage(Map<String, dynamic> data) {
    final type = data['type'];
    debugPrint('Handling WebSocket message type: $type');

    switch (type) {
      case 'new_message':
        try {
          final messageData = data['message'];
          if (messageData == null) {
            debugPrint('Warning: new_message received but message data is null');
            break;
          }
          final currentUserId = _authService?.currentUser?.id;
          final message = ChatMessage.fromJson(messageData, currentUserId: currentUserId);
          debugPrint('New message received: ${message.text} from ${message.userName}');

          // Update username cache in conversation service if available
          if (message.userId != null && message.userName != null && _conversationService != null) {
            _conversationService!.updateUsernameCache(message.userId!, message.userName!);
          }

          // Ignore if message is from current user (handled by message_sent)
          if (currentUserId != null && message.userId == currentUserId) {
            debugPrint('Ignoring new_message from current user (already handled by message_sent)');
            break;
          }

          // Show notification for new message (if not viewing this conversation)
          _showNotificationForMessage(message);

          // Check conversation ID match
          if (message.conversationId == _currentConversationId) {
            // Check if message already exists to avoid duplicates
            final exists = _messages.any((m) => m.id == message.id);
            if (!exists) {
              _messages.add(message);
              notifyListeners();
              debugPrint('Message added to chat: ${message.text}');
            } else {
              debugPrint('Message already exists, skipping duplicate');
            }
          } else {
            debugPrint('Message for different conversation: ${message.conversationId} vs $_currentConversationId');
            debugPrint('Current conversation ID: $_currentConversationId');
            debugPrint('Message conversation ID: ${message.conversationId}');

            // Handle case where there's no current conversation - load the conversation and add the message
            if (_currentConversationId == null && message.conversationId != null) {
              debugPrint('No current conversation set. Loading conversation and adding message.');
              // Try to load the conversation first, then add the message
              _handleMessageForDifferentConversation(message, currentUserId).catchError((e) {
                debugPrint('Error loading conversation for received message: $e');
                // If loading fails, at least set the conversation ID and add the message
                _currentConversationId = message.conversationId;
                _webSocketService?.joinConversation(message.conversationId!);
                final exists = _messages.any((m) => m.id == message.id);
                if (!exists) {
                  _messages.add(message);
                  notifyListeners();
                  debugPrint('Message added (conversation load failed): ${message.text}');
                }
              });
            }
            // Handle case where message is for a different conversation
            // Don't automatically load/open it - just show notification
            else if (message.conversationId != null) {
              debugPrint('Message for different conversation: ${message.conversationId}');
              debugPrint('Not loading conversation automatically - notification will be shown');
              // Just ensure the conversation exists in the list, but don't open it
              if (_conversationService != null) {
                _ensureConversationInList(message.conversationId!, currentUserId).catchError((e) {
                  debugPrint('Error ensuring conversation in list: $e');
                });
              }
            }
          }
        } catch (e) {
          debugPrint('Error handling new_message: $e');
          debugPrint('Message data: $data');
        }
        break;

      case 'message_sent':
        try {
          final messageData = data['message'];
          if (messageData == null) {
            debugPrint('Warning: message_sent received but message data is null');
            break;
          }
          final currentUserId = _authService?.currentUser?.id;
          final message = ChatMessage.fromJson(messageData, currentUserId: currentUserId);
          debugPrint('Message sent confirmation: ${message.text}');

          // Update username cache in conversation service if available
          if (message.userId != null && message.userName != null && _conversationService != null) {
            _conversationService!.updateUsernameCache(message.userId!, message.userName!);
          }

          // Only process if this is for the current conversation
          if (message.conversationId != _currentConversationId) {
            debugPrint('message_sent for different conversation: ${message.conversationId} vs $_currentConversationId');
            break;
          }

          // Get clientMessageId from the message data (server echoes it back)
          final clientMessageId = messageData['clientMessageId'] as String?;
          debugPrint('message_sent - clientMessageId from server: $clientMessageId');
          debugPrint('message_sent - server message ID: ${message.id}');
          debugPrint('message_sent - current messages count: ${_messages.length}');
          debugPrint('message_sent - looking for message with text: ${message.text}');

          // Log all current messages for debugging
          for (int i = 0; i < _messages.length; i++) {
            final m = _messages[i];
            debugPrint('message_sent - message[$i]: id=${m.id}, clientId=${m.clientMessageId}, text=${m.text}');
          }

          // Update local message if needed (replace optimistic message)
          // Match by clientMessageId first (most reliable), then by ID, then by text/userId/timestamp
          int? matchedIndex;
          String? matchMethod;

          if (clientMessageId != null) {
            // Try to match by clientMessageId first
            matchedIndex = _messages.indexWhere((m) => m.clientMessageId == clientMessageId);
            if (matchedIndex != -1) {
              matchMethod = 'clientMessageId';
              debugPrint('message_sent - Matched by clientMessageId: $clientMessageId at index $matchedIndex');
            }
          }

          // If not matched by clientMessageId, try by server ID
          if (matchedIndex == null || matchedIndex == -1) {
            matchedIndex = _messages.indexWhere((m) => m.id == message.id);
            if (matchedIndex != -1) {
              matchMethod = 'ID';
              debugPrint('message_sent - Matched by ID: ${message.id} at index $matchedIndex');
            }
          }

          // If still not matched, try by text/userId/timestamp (fallback)
          if (matchedIndex == null || matchedIndex == -1) {
            matchedIndex = _messages.indexWhere((m) =>
              m.text == message.text &&
              m.userId == message.userId &&
              m.createdAt.difference(message.createdAt).inSeconds.abs() < 5
            );
            if (matchedIndex != -1) {
              matchMethod = 'text/userId/timestamp';
              debugPrint('message_sent - Matched by text/userId/timestamp at index $matchedIndex');
            }
          }

          final index = matchedIndex ?? -1;

          if (index != -1) {
            // Replace optimistic message with server-confirmed message
            // Preserve clientMessageId if it exists in the original message
            final originalClientId = _messages[index].clientMessageId;
            final updatedMessage = ChatMessage(
              id: message.id,
              text: message.text,
              createdAt: message.createdAt,
              isUser: message.isUser,
              imageUrl: message.imageUrl,
              type: message.type,
              userId: message.userId,
              userName: message.userName,
              conversationId: message.conversationId,
              isBot: message.isBot,
              clientMessageId: originalClientId ?? clientMessageId, // Preserve original or use from server
            );
            _messages[index] = updatedMessage;
            debugPrint('Updated existing message with server confirmation (matched by $matchMethod)');
          } else {
            // If not found, add it (shouldn't happen, but handle gracefully)
            debugPrint('WARNING: Message not found in local list, adding it');
            debugPrint('This might cause a duplicate. Check if conversation_history cleared it too early.');
            _messages.add(message);
          }
          notifyListeners();
        } catch (e) {
          debugPrint('Error handling message_sent: $e');
          debugPrint('Message data: $data');
        }
        break;

      case 'conversation_history':
        try {
          final conversationId = data['conversationId'];
          if (conversationId == _currentConversationId) {
            final messagesList = data['messages'] as List?;
            if (messagesList != null) {
              debugPrint('Loading conversation history: ${messagesList.length} messages');
              final currentUserId = _authService?.currentUser?.id;

              // If we're currently loading the conversation via API, don't clear messages
              // The API load already populated them, and we just need to merge/update
              if (_isLoadingConversation) {
                debugPrint('Conversation is being loaded via API, handling conversation_history');
                _conversationHistoryReceived = true; // Mark that we received history

                final historyMessages = messagesList
                    .map((msg) => ChatMessage.fromJson(msg, currentUserId: currentUserId))
                    .toList();

                // If messages are already loaded from API, check for duplicates
                if (_messages.isNotEmpty) {
                  debugPrint('Messages already loaded from API, checking for duplicates');
                  final existingIds = _messages.map((m) => m.id).toSet();
                  final historyIds = historyMessages.map((m) => m.id).toSet();

                  if (existingIds.length == historyIds.length &&
                      existingIds.every((id) => historyIds.contains(id))) {
                    debugPrint('Messages already loaded from API, skipping conversation_history');
                    _isLoadingConversation = false; // Reset flag since we're done
                    _conversationHistoryReceived = false;
                    return; // Exit early, messages are already loaded
                  }

                  // Merge messages: add only new ones that don't exist
                  for (final historyMsg in historyMessages) {
                    final exists = _messages.any((m) => m.id == historyMsg.id);
                    if (!exists) {
                      _messages.add(historyMsg);
                    }
                  }

                  // Sort messages by timestamp to maintain order
                  _messages.sort((a, b) => a.createdAt.compareTo(b.createdAt));
                  _isLoadingConversation = false; // Reset flag after merging
                  _conversationHistoryReceived = false;
                  notifyListeners();
                  return; // Exit early, don't clear messages
                } else {
                  // Messages not loaded from API yet, but conversation_history arrived first
                  // Add the messages now, and API will skip loading
                  debugPrint('conversation_history arrived before API load, adding messages now');
                  _messages.addAll(historyMessages);
                  _isLoadingConversation = false; // Reset flag since we got history
                  _conversationHistoryReceived = false;
                  notifyListeners();
                  return; // Exit early, don't clear messages
                }
              }

              // Preserve optimistic messages (those with clientMessageId) when loading history
              // Only preserve messages that are recent (sent in last 10 seconds) to avoid keeping stale ones
              final now = DateTime.now();
              final optimisticMessages = _messages.where((m) =>
                m.clientMessageId != null &&
                m.conversationId == conversationId &&
                now.difference(m.createdAt).inSeconds < 10 // Only recent optimistic messages
              ).toList();

              debugPrint('Preserving ${optimisticMessages.length} recent optimistic messages');

              // Before clearing, check if we're in the middle of handling a message for different conversation
              // If so, we should merge instead of clearing to avoid losing the message that triggered the load
              final historyMessages = messagesList
                  .map((msg) => ChatMessage.fromJson(msg, currentUserId: currentUserId))
                  .toList();

              // Check if all history messages already exist in current messages
              final existingIds = _messages.map((m) => m.id).toSet();
              final historyIds = historyMessages.map((m) => m.id).toSet();

              if (existingIds.length == historyIds.length &&
                  existingIds.every((id) => historyIds.contains(id))) {
                debugPrint('All conversation_history messages already exist, skipping reload');
                // Just update isUser flags if needed
                notifyListeners();
                return;
              }

              // Clear and reload from history
              _messages.clear();
              _messages.addAll(historyMessages);

              // Re-add optimistic messages that haven't been confirmed yet
              // Match by checking if any history message has the same clientMessageId
              for (final optimisticMsg in optimisticMessages) {
                // Check both in parsed messages and raw JSON data
                final existsInHistory = historyMessages.any((m) =>
                  m.clientMessageId != null && m.clientMessageId == optimisticMsg.clientMessageId
                ) || (messagesList as List).any((msgJson) {
                  // Also check raw JSON for clientMessageId
                  final rawClientId = (msgJson as Map<String, dynamic>)['clientMessageId'] as String?;
                  return rawClientId != null && rawClientId == optimisticMsg.clientMessageId;
                });

                if (!existsInHistory) {
                  debugPrint('Re-adding optimistic message with clientMessageId: ${optimisticMsg.clientMessageId}');
                  _messages.add(optimisticMsg);
                } else {
                  debugPrint('Optimistic message already in history, skipping: ${optimisticMsg.clientMessageId}');
                }
              }

              notifyListeners();
            }
          }
        } catch (e) {
          debugPrint('Error handling conversation_history: $e');
          debugPrint('Message data: $data');
        }
        break;

      case 'bot_added':
        // Bot was added to conversation
        debugPrint('Bot added to conversation');
        final botAddedConversationId = data['conversationId'] as String?;
        if (botAddedConversationId == _currentConversationId && botAddedConversationId != null) {
          // Show notification message for all participants
          final notificationMessage = ChatMessage(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            text: '🤖 AI Bot has been added to the conversation',
            createdAt: DateTime.now(),
            isUser: false,
            userId: 'system',
            userName: 'System',
            conversationId: botAddedConversationId,
            isBot: false,
          );
          _messages.add(notificationMessage);
          notifyListeners();
        }
        break;

      case 'bot_removed':
        // Bot was removed from conversation
        debugPrint('Bot removed from conversation');
        final botRemovedConversationId = data['conversationId'] as String?;
        if (botRemovedConversationId == _currentConversationId && botRemovedConversationId != null) {
          // Show notification message for all participants
          final notificationMessage = ChatMessage(
            id: DateTime.now().millisecondsSinceEpoch.toString(),
            text: '💬 Normal chat mode enabled. AI Bot has been removed from the conversation',
            createdAt: DateTime.now(),
            isUser: false,
            userId: 'system',
            userName: 'System',
            conversationId: botRemovedConversationId,
            isBot: false,
          );
          _messages.add(notificationMessage);
          notifyListeners();
        }
        break;

      case 'group_created':
        try {
          final conversationData = data['conversation'];
          if (conversationData != null && _conversationService != null) {
            final conversation = Conversation.fromJson(conversationData);
            _conversationService!.addOrUpdateConversation(conversation);
            debugPrint('New group created: ${conversation.name ?? conversation.id}');
          }
        } catch (e) {
          debugPrint('Error handling group_created: $e');
        }
        break;

      case 'user_joined_group':
      case 'user_left_group':
        try {
          final conversationData = data['conversation'];
          if (conversationData != null && _conversationService != null) {
            final conversation = Conversation.fromJson(conversationData);
            _conversationService!.addOrUpdateConversation(conversation);
            debugPrint('Group updated: ${conversation.name ?? conversation.id}');
          }
        } catch (e) {
          debugPrint('Error handling group update: $e');
        }
        break;

      case 'all_groups':
        try {
          final conversationsList = data['conversations'] as List?;
          if (conversationsList != null && _conversationService != null) {
            final conversations = conversationsList
                .map((conv) => Conversation.fromJson(conv))
                .toList();
            _conversationService!.loadConversations(conversations);
            debugPrint('Loaded ${conversations.length} conversations');
          }
        } catch (e) {
          debugPrint('Error handling all_groups: $e');
        }
        break;

      default:
        debugPrint('Unknown WebSocket message type: $type');
        debugPrint('Message data: $data');
    }
  }

  Future<void> loadConversation(String conversationId) async {
    _currentConversationId = conversationId;
    // Update notification service to track current conversation
    _notificationService.setCurrentConversationId(conversationId);
    // Cancel any existing notifications for this conversation
    _notificationService.cancelConversationNotifications(conversationId);
    _messages.clear();
    _isLoadingConversation = true; // Set flag to prevent conversation_history from clearing
    _conversationHistoryReceived = false; // Reset flag

    try {
      // Join conversation via WebSocket (this will trigger conversation_history)
      _webSocketService?.joinConversation(conversationId);

      // Load messages from API
      if (_conversationService != null) {
        final loadedMessages = await _conversationService!.getMessages(conversationId);

        // If conversation_history already arrived and populated messages, skip API loading
        if (_conversationHistoryReceived && _messages.isNotEmpty) {
          debugPrint('conversation_history already loaded messages, skipping API load');
          // Update isUser flags for existing messages (rebuild list since ChatMessage is immutable)
          final currentUserId = _authService?.currentUser?.id;
          if (currentUserId != null) {
            final updatedMessages = _messages.map((msg) {
              if (msg.userId == currentUserId && !msg.isUser) {
                return ChatMessage(
                  id: msg.id,
                  text: msg.text,
                  createdAt: msg.createdAt,
                  isUser: true,
                  imageUrl: msg.imageUrl,
                  type: msg.type,
                  userId: msg.userId,
                  userName: msg.userName,
                  conversationId: msg.conversationId,
                  isBot: msg.isBot,
                  clientMessageId: msg.clientMessageId,
                );
              }
              return msg;
            }).toList();
            _messages.clear();
            _messages.addAll(updatedMessages);
          }
          _isLoadingConversation = false;
          notifyListeners();
          return;
        }

        final currentUserId = _authService?.currentUser?.id;

        // Update isUser for each message based on current user
        final messagesWithIsUser = loadedMessages.map((msg) {
          if (currentUserId != null && msg.userId == currentUserId) {
            // Create a new message with isUser set correctly
            return ChatMessage(
              id: msg.id,
              text: msg.text,
              createdAt: msg.createdAt,
              isUser: true,
              imageUrl: msg.imageUrl,
              type: msg.type,
              userId: msg.userId,
              userName: msg.userName,
              conversationId: msg.conversationId,
              isBot: msg.isBot,
            );
          }
          return msg;
        }).toList();

        // Only add messages if they don't already exist (in case conversation_history added them)
        for (final msg in messagesWithIsUser) {
          final exists = _messages.any((m) => m.id == msg.id);
          if (!exists) {
            _messages.add(msg);
          }
        }

        // Sort messages by timestamp to maintain order
        _messages.sort((a, b) => a.createdAt.compareTo(b.createdAt));
        _isLoadingConversation = false;
        notifyListeners();
      }
    } finally {
      // Reset flag after a delay as fallback (in case conversation_history never arrives)
      Future.delayed(const Duration(milliseconds: 2000), () {
        if (_isLoadingConversation) {
          debugPrint('Resetting _isLoadingConversation flag after timeout');
          _isLoadingConversation = false;
          _conversationHistoryReceived = false;
        }
      });
    }
  }

  Future<void> sendTextMessage(String text) async {
    if (text.trim().isEmpty || _currentConversationId == null) return;

    // Check for /bot command
    if (text.trim() == '/bot') {
      await _handleBotCommand();
      return;
    }

    // Check for /chat command
    if (text.trim() == '/chat') {
      await _handleChatCommand();
      return;
    }

    final user = _authService?.currentUser;
    if (user == null || _webSocketService == null) {
      debugPrint('User not authenticated or WebSocket not connected');
      return;
    }

    // Send via WebSocket
    try {
      if (!_webSocketService!.isConnected) {
        debugPrint('WebSocket not connected. Attempting to reconnect...');
        await _webSocketService!.connect(user.id);
      }

      // Generate clientMessageId for matching optimistic message with server response
      final clientMessageId = DateTime.now().millisecondsSinceEpoch.toString() + '_' + user.id.substring(0, 8);

      // Optimistically add message (will be confirmed by WebSocket)
      final optimisticMessage = ChatMessage(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        text: text.trim(),
        createdAt: DateTime.now(),
        isUser: true,
        userId: user.id,
        userName: user.username,
        conversationId: _currentConversationId,
        isBot: false,
        clientMessageId: clientMessageId,
      );

      _messages.add(optimisticMessage);
      notifyListeners();

      _webSocketService!.sendMessage(
        text: text.trim(),
        conversationId: _currentConversationId!,
        userName: user.username,
        userId: user.id,
        clientMessageId: clientMessageId,
      );

      debugPrint('Message sent successfully: ${text.trim()}');
    } catch (e) {
      debugPrint('Error sending message: $e');
      // Remove optimistic message if sending failed
      if (_messages.isNotEmpty && _messages.last.text == text.trim()) {
        _messages.removeLast();
        notifyListeners();
      }
      rethrow;
    }
  }

  Future<void> _handleBotCommand() async {
    if (_currentConversationId == null || _conversationService == null) return;

    try {
      await _conversationService!.addBotToConversation(_currentConversationId!);
      // Notification message will be added via WebSocket bot_added event
      // so all participants see it
    } catch (e) {
      debugPrint('Error adding bot: $e');
    }
  }

  Future<void> _handleChatCommand() async {
    if (_currentConversationId == null || _conversationService == null) return;

    try {
      await _conversationService!.removeBotFromConversation(_currentConversationId!);
      // Notification message will be added via WebSocket bot_removed event
      // so all participants see it
    } catch (e) {
      debugPrint('Error removing bot: $e');
    }
  }

  Future<void> sendImageMessage(String imagePath) async {
    if (_currentConversationId == null) return;

    final user = _authService?.currentUser;
    if (user == null || _webSocketService == null) {
      debugPrint('User not authenticated or WebSocket not connected');
      return;
    }

    // For now, send as text message with image path
    // In production, you'd upload the image first and send the URL
    final imageMessage = ChatMessage(
      id: DateTime.now().millisecondsSinceEpoch.toString(),
      text: "📷 Image shared",
      createdAt: DateTime.now(),
      isUser: true,
      imageUrl: imagePath,
      type: MessageType.image,
      userId: user.id,
      userName: user.username,
      conversationId: _currentConversationId,
      isBot: false,
    );

    _messages.add(imageMessage);
    notifyListeners();

    // Send via WebSocket
    try {
      if (!_webSocketService!.isConnected) {
        debugPrint('WebSocket not connected. Attempting to reconnect...');
        await _webSocketService!.connect(user.id);
      }

      _webSocketService!.sendMessage(
        text: "📷 Image shared",
        conversationId: _currentConversationId!,
        userName: user.username,
        userId: user.id,
      );
    } catch (e) {
      debugPrint('Error sending image message: $e');
    }
  }

  Future<void> startListening() async {
    if (!_speechToText.isAvailable) return;

    _isListening = true;
    notifyListeners();

    await _speechToText.listen(
      onResult: (result) {
        if (result.finalResult) {
          _isListening = false;
          notifyListeners();

          if (result.recognizedWords.isNotEmpty) {
            sendTextMessage(result.recognizedWords);
          }
        }
      },
      listenFor: const Duration(seconds: 30),
      pauseFor: const Duration(seconds: 3),
      partialResults: true,
      localeId: "en_US",
      onSoundLevelChange: (level) {
        // Handle sound level changes if needed
      },
    );
  }

  Future<void> stopListening() async {
    await _speechToText.stop();
    _isListening = false;
    notifyListeners();
  }

  Future<String?> pickImageFromCamera() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.camera,
        imageQuality: 80,
      );
      return image?.path;
    } catch (e) {
      debugPrint('Error picking image from camera: $e');
      return null;
    }
  }

  Future<String?> pickImageFromGallery() async {
    try {
      final XFile? image = await _imagePicker.pickImage(
        source: ImageSource.gallery,
        imageQuality: 80,
      );
      return image?.path;
    } catch (e) {
      debugPrint('Error picking image from gallery: $e');
      return null;
    }
  }

  void clearMessages() {
    _messages.clear();
    notifyListeners();
  }

  void clearConversation() {
    _currentConversationId = null;
    _notificationService.setCurrentConversationId(null);
    _messages.clear();
    notifyListeners();
  }

  /// Ensure conversation exists in the list without opening it
  Future<void> _ensureConversationInList(String conversationId, String? currentUserId) async {
    try {
      // Check if conversation already exists in list
      final conversations = _conversationService!.conversations;
      final conversationExists = conversations.any((c) => c.id == conversationId);

      if (!conversationExists) {
        // Fetch the conversation to add it to the list
        final conversation = await _conversationService!.getConversation(conversationId);

        // Check if current user is a participant
        final isParticipant = conversation.participants.contains(currentUserId);

        if (isParticipant) {
          debugPrint('Adding conversation to list: ${conversation.id}');
          _conversationService!.loadConversations([...conversations, conversation]);
        }
      }
    } catch (e) {
      debugPrint('Error ensuring conversation in list: $e');
      // Don't rethrow - this is not critical
    }
  }

  Future<void> _handleMessageForDifferentConversation(
    ChatMessage message,
    String? currentUserId,
  ) async {
    try {
      // Fetch the conversation
      final conversation = await _conversationService!.getConversation(message.conversationId!);

      // Check if current user is a participant
      final isParticipant = conversation.participants.contains(currentUserId);

      if (isParticipant) {
        debugPrint('User is a participant in this conversation. Loading conversation...');

        // Add conversation to the list if it's not already there
        final conversations = _conversationService!.conversations;
        final conversationExists = conversations.any((c) => c.id == conversation.id);
        if (!conversationExists) {
          debugPrint('Adding conversation to list: ${conversation.id}');
          _conversationService!.loadConversations([...conversations, conversation]);
        }

        // Set as current conversation in ConversationService
        _conversationService!.setCurrentConversation(conversation);

        // Load the conversation and switch to it
        // Note: loadConversation() will trigger conversation_history which includes this message
        // So we don't need to manually add it - conversation_history will handle it
        await loadConversation(message.conversationId!);

        // Double-check: if message still doesn't exist after loading, add it
        // This handles the edge case where conversation_history doesn't include it
        final exists = _messages.any((m) => m.id == message.id);
        if (!exists) {
          debugPrint('Message not found after loadConversation, adding manually: ${message.text}');
          _messages.add(message);
          notifyListeners();
        } else {
          debugPrint('Message already loaded via conversation_history: ${message.text}');
        }
      } else {
        debugPrint('User is not a participant in this conversation. Ignoring message.');
      }
    } catch (e) {
      debugPrint('Error loading conversation for received message: $e');
      rethrow; // Re-throw to be caught by caller
    }
  }

  /// Show notification for a new message
  Future<void> _showNotificationForMessage(ChatMessage message) async {
    debugPrint('_showNotificationForMessage called: conversationId=${message.conversationId}, userName=${message.userName}, currentConversationId=$_currentConversationId');

    if (message.conversationId == null || message.userName == null) {
      debugPrint('Skipping notification: missing conversationId or userName');
      return;
    }

    // Get conversation name from conversation service
    String? conversationName;
    if (_conversationService != null) {
      try {
        final conversation = _conversationService!.conversations.firstWhere(
          (c) => c.id == message.conversationId,
        );
        conversationName = conversation.name;
        debugPrint('Found conversation name for notification: $conversationName');
      } catch (e) {
        // Conversation not found in list, use sender name as fallback
        debugPrint('Conversation not found for notification: ${message.conversationId}, will use sender name');
      }
    }

    // Show notification
    debugPrint('Calling notificationService.showMessageNotification...');
    final result = await _notificationService.showMessageNotification(
      conversationId: message.conversationId!,
      messageText: message.text,
      senderName: message.userName!,
      conversationName: conversationName,
    );
    debugPrint('Notification result: $result (true=shown, false=suppressed)');
  }

  @override
  void dispose() {
    _messageSubscription?.cancel();
    _messageSubscription = null;
    super.dispose();
  }
}
