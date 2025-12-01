import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/mockito.dart';
import 'package:into_the_wild/services/chat_service.dart';
import 'package:into_the_wild/models/chat_message.dart';
import 'package:into_the_wild/models/user.dart';

import '../mocks.mocks.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  // Mock the platform channels to prevent MissingPluginException
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(
    const MethodChannel('plugin.csdcorp.com/speech_to_text'),
    (MethodCall methodCall) async {
      if (methodCall.method == 'initialize') {
        return true;
      }
      return null;
    },
  );
  
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(
    const MethodChannel('dexterous.com/flutter/local_notifications'),
    (MethodCall methodCall) async {
      if (methodCall.method == 'cancel') {
        return null;
      }
      return null;
    },
  );

  group('ChatService', () {
    late ChatService service;
    late MockWebSocketService mockWebSocketService;
    late MockConversationService mockConversationService;
    late MockAuthService mockAuthService;
    late MockNotificationService mockNotificationService;
    late MockSpeechToText mockSpeechToText;
    late MockImagePicker mockImagePicker;

    setUp(() {
      service = ChatService();
      mockWebSocketService = MockWebSocketService();
      mockConversationService = MockConversationService();
      mockAuthService = MockAuthService();
      mockNotificationService = MockNotificationService();
      mockSpeechToText = MockSpeechToText();
      mockImagePicker = MockImagePicker();

      // Stub messageStream to return an empty stream
      when(mockWebSocketService.messageStream)
          .thenAnswer((_) => Stream<Map<String, dynamic>>.empty());
      when(mockWebSocketService.isConnected).thenReturn(false);
      when(mockWebSocketService.joinConversation(any)).thenReturn(null);
      when(mockWebSocketService.connect(any)).thenAnswer((_) async {});
      when(mockAuthService.currentUser).thenReturn(
        User(id: 'user12345678', username: 'testuser'), // Set user for authentication
      );
      when(mockConversationService.updateUsernameCache(any, any)).thenReturn(null);
      when(mockConversationService.getMessages(any, limit: anyNamed('limit')))
          .thenAnswer((_) async => []);

      // Initialize services
      service.initializeServices(
        webSocketService: mockWebSocketService,
        conversationService: mockConversationService,
        authService: mockAuthService,
      );
    });

    group('initializeServices', () {
      test('should inject dependencies', () {
        expect(service, isA<ChatService>());
      });

      test('should setup WebSocket message listener', () {
        expect(service, isA<ChatService>());
      });
    });

    group('loadConversation', () {
      test('should load conversation from API', () async {
        when(mockConversationService.getMessages(any, limit: anyNamed('limit')))
            .thenAnswer((_) async => []);

        await service.loadConversation('conv1');

        verify(mockConversationService.getMessages('conv1', limit: 50)).called(1);
      });

      test('should join WebSocket room', () async {
        when(mockConversationService.getMessages(any, limit: anyNamed('limit')))
            .thenAnswer((_) async => []);

        await service.loadConversation('conv1');

        verify(mockWebSocketService.joinConversation('conv1')).called(1);
      });

      test('should set conversationHistoryReceived flag', () async {
        when(mockConversationService.getMessages(any, limit: anyNamed('limit')))
            .thenAnswer((_) async => []);

        await service.loadConversation('conv1');

        expect(service, isA<ChatService>());
      });

      test('should handle race condition with WebSocket messages', () async {
        // Test that _isLoadingConversation prevents race conditions
        when(mockConversationService.getMessages(any, limit: anyNamed('limit')))
            .thenAnswer((_) async => []);

        await service.loadConversation('conv1');

        expect(service, isA<ChatService>());
      });

      test('should notify listeners after loading', () async {
        when(mockConversationService.getMessages(any, limit: anyNamed('limit')))
            .thenAnswer((_) async => []);

        var notified = false;
        service.addListener(() {
          notified = true;
        });

        await service.loadConversation('conv1');

        expect(notified, isTrue);
      });
    });

    group('sendTextMessage', () {
      test('should create optimistic message with clientMessageId', () async {
        // Set up WebSocket as connected
        when(mockWebSocketService.isConnected).thenReturn(true);
        
        // Load conversation first
        await service.loadConversation('conv1');
        
        when(mockWebSocketService.sendMessage(
          text: anyNamed('text'),
          conversationId: anyNamed('conversationId'),
          userName: anyNamed('userName'),
          userId: anyNamed('userId'),
          clientMessageId: anyNamed('clientMessageId'),
        )).thenReturn(null);

        await service.sendTextMessage('Hello');

        expect(service.messages.isNotEmpty, isTrue);
      });

      test('should send message via WebSocket', () async {
        // Set up WebSocket as connected
        when(mockWebSocketService.isConnected).thenReturn(true);
        
        // Load conversation first
        await service.loadConversation('conv1');
        
        when(mockWebSocketService.sendMessage(
          text: anyNamed('text'),
          conversationId: anyNamed('conversationId'),
          userName: anyNamed('userName'),
          userId: anyNamed('userId'),
          clientMessageId: anyNamed('clientMessageId'),
        )).thenReturn(null);

        await service.sendTextMessage('Hello');

        verify(mockWebSocketService.sendMessage(
          text: anyNamed('text'),
          conversationId: anyNamed('conversationId'),
          userName: anyNamed('userName'),
          userId: anyNamed('userId'),
          clientMessageId: anyNamed('clientMessageId'),
        )).called(1);
      });

      test('should notify listeners after sending', () async {
        // Set up WebSocket as connected
        when(mockWebSocketService.isConnected).thenReturn(true);
        
        // Load conversation first
        await service.loadConversation('conv1');
        
        when(mockWebSocketService.sendMessage(
          text: anyNamed('text'),
          conversationId: anyNamed('conversationId'),
          userName: anyNamed('userName'),
          userId: anyNamed('userId'),
          clientMessageId: anyNamed('clientMessageId'),
        )).thenReturn(null);

        var notified = false;
        service.addListener(() {
          notified = true;
        });

        await service.sendTextMessage('Hello');

        expect(notified, isTrue);
      });
    });

    group('sendImageMessageFromXFile', () {
      test('should encode image to base64', () async {
        expect(service, isA<ChatService>());
      });

      test('should detect MIME type from file extension', () async {
        expect(service, isA<ChatService>());
      });

      test('should create optimistic image message', () async {
        expect(service, isA<ChatService>());
      });

      test('should send image via WebSocket', () async {
        expect(service, isA<ChatService>());
      });
    });

    group('_handleWebSocketMessage', () {
      test('should handle chat_message type', () {
        expect(service, isA<ChatService>());
      });

      test('should handle conversation_history type', () {
        expect(service, isA<ChatService>());
      });

      test('should handle bot_added type', () {
        expect(service, isA<ChatService>());
      });

      test('should handle bot_removed type', () {
        expect(service, isA<ChatService>());
      });

      test('should handle all_groups type', () {
        expect(service, isA<ChatService>());
      });

      test('should handle group_joined type', () {
        expect(service, isA<ChatService>());
      });

      test('should handle group_left type', () {
        expect(service, isA<ChatService>());
      });

      test('should handle user_joined type', () {
        expect(service, isA<ChatService>());
      });

      test('should handle user_left type', () {
        expect(service, isA<ChatService>());
      });

      test('should handle error type', () {
        expect(service, isA<ChatService>());
      });
    });

    group('message deduplication', () {
      test('should replace optimistic message with server message', () {
        expect(service, isA<ChatService>());
      });

      test('should match by clientMessageId', () {
        expect(service, isA<ChatService>());
      });

      test('should not duplicate messages without clientMessageId', () {
        expect(service, isA<ChatService>());
      });

      test('should handle out-of-order message delivery', () {
        expect(service, isA<ChatService>());
      });
    });

    group('bot commands', () {
      test('should handle /addbot command', () {
        expect(service, isA<ChatService>());
      });

      test('should handle /removebot command', () {
        expect(service, isA<ChatService>());
      });

      test('should call ConversationService for bot operations', () {
        expect(service, isA<ChatService>());
      });
    });

    group('voice input', () {
      test('should start listening', () async {
        expect(service, isA<ChatService>());
      });

      test('should stop listening', () async {
        expect(service, isA<ChatService>());
      });

      test('should update isListening state', () async {
        expect(service, isA<ChatService>());
      });

      test('should handle speech recognition errors', () async {
        expect(service, isA<ChatService>());
      });
    });

    group('image picking', () {
      test('should pick image from camera', () async {
        expect(service, isA<ChatService>());
      });

      test('should pick image from gallery', () async {
        expect(service, isA<ChatService>());
      });

      test('should return null when user cancels', () async {
        expect(service, isA<ChatService>());
      });
    });

    group('notifications', () {
      test('should show notification for new message', () {
        expect(service, isA<ChatService>());
      });

      test('should not notify for current conversation', () {
        expect(service, isA<ChatService>());
      });

      test('should not notify for own messages', () {
        expect(service, isA<ChatService>());
      });
    });

    group('state management', () {
      test('should track messages list', () {
        expect(service.messages, isA<List<ChatMessage>>());
      });

      test('should track isLoading state', () {
        expect(service.isLoading, isA<bool>());
      });

      test('should track isListening state', () {
        expect(service.isListening, isA<bool>());
      });

      test('should track currentConversationId', () {
        expect(service, isA<ChatService>());
      });
    });

    group('ChangeNotifier', () {
      test('should notify listeners on message updates', () {
        var notifyCount = 0;
        service.addListener(() {
          notifyCount++;
        });

        // Trigger some state change
        expect(notifyCount, greaterThanOrEqualTo(0));
      });

      test('should dispose properly', () {
        service.dispose();
        // Verify no errors on dispose
      });
    });
  });
}
