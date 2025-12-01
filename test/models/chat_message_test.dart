import 'package:flutter_test/flutter_test.dart';
import 'package:into_the_wild/models/chat_message.dart';

void main() {
  group('ChatMessage', () {
    group('fromJson', () {
      test('should parse message with ISO DateTime string', () {
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
        };

        final message = ChatMessage.fromJson(json);

        expect(message.id, '123');
        expect(message.text, 'Hello');
        expect(message.createdAt, isA<DateTime>());
        expect(message.userId, 'user1');
        expect(message.userName, 'John');
        expect(message.conversationId, 'conv1');
        expect(message.isUser, isFalse);
        expect(message.isBot, isFalse);
        expect(message.imageUrl, isNull);
        expect(message.type, MessageType.text);
      });

      test('should parse message with timestamp (int milliseconds)', () {
        final timestamp = DateTime(2025, 11, 30, 10, 30).millisecondsSinceEpoch;
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': timestamp,
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
        };

        final message = ChatMessage.fromJson(json);

        expect(message.createdAt, isA<DateTime>());
        expect(message.createdAt.year, 2025);
        expect(message.createdAt.month, 11);
        expect(message.createdAt.day, 30);
      });

      test('should parse message with DateTime object', () {
        final dateTime = DateTime(2025, 11, 30, 10, 30);
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': dateTime,
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
        };

        final message = ChatMessage.fromJson(json);

        expect(message.createdAt, dateTime);
      });

      test('should handle null createdAt', () {
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': null,
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
        };

        final message = ChatMessage.fromJson(json);

        expect(message.createdAt, isA<DateTime>());
        // Should default to current time (approximately)
        expect(
          message.createdAt.difference(DateTime.now()).abs(),
          lessThan(Duration(seconds: 1)),
        );
      });

      test('should derive isUser=true when userId matches currentUserId', () {
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
        };

        final message = ChatMessage.fromJson(json, currentUserId: 'user1');

        expect(message.isUser, isTrue);
      });

      test('should derive isUser=false when userId does not match currentUserId', () {
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
        };

        final message = ChatMessage.fromJson(json, currentUserId: 'user2');

        expect(message.isUser, isFalse);
      });

      test('should derive isUser=false when currentUserId is null', () {
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
        };

        final message = ChatMessage.fromJson(json);

        expect(message.isUser, isFalse);
      });

      test('should parse isBot flag', () {
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'userId': 'bot1',
          'userName': 'Bot',
          'conversationId': 'conv1',
          'isBot': true,
        };

        final message = ChatMessage.fromJson(json);

        expect(message.isBot, isTrue);
      });

      test('should default isBot to false when not provided', () {
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
        };

        final message = ChatMessage.fromJson(json);

        expect(message.isBot, isFalse);
      });

      test('should parse image message', () {
        final json = {
          'id': '123',
          'text': 'Check this out',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
          'imageUrl': 'https://example.com/image.jpg',
          'type': 'image',
        };

        final message = ChatMessage.fromJson(json);

        expect(message.imageUrl, 'https://example.com/image.jpg');
        expect(message.type, MessageType.image);
      });

      test('should parse message with clientMessageId', () {
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
          'clientMessageId': 'client-123',
        };

        final message = ChatMessage.fromJson(json);

        expect(message.clientMessageId, 'client-123');
      });

      test('should handle all nullable fields being null', () {
        final json = {
          'id': '123',
          'text': 'Hello',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'userId': 'user1',
          'userName': 'John',
          'conversationId': 'conv1',
        };

        final message = ChatMessage.fromJson(json);

        expect(message.imageUrl, isNull);
        expect(message.clientMessageId, isNull);
      });
    });

    group('toJson', () {
      test('should serialize message to JSON', () {
        final message = ChatMessage(
          id: '123',
          text: 'Hello',
          createdAt: DateTime(2025, 11, 30, 10, 30),
          isUser: true,
          userId: 'user1',
          userName: 'John',
          conversationId: 'conv1',
          isBot: false,
          type: MessageType.text,
        );

        final json = message.toJson();

        expect(json['id'], '123');
        expect(json['text'], 'Hello');
        expect(json['createdAt'], isA<String>());
        expect(json['isUser'], isTrue);
        expect(json['userId'], 'user1');
        expect(json['userName'], 'John');
        expect(json['conversationId'], 'conv1');
        expect(json['isBot'], isFalse);
        expect(json['type'], 'text');
      });

      test('should serialize image message to JSON', () {
        final message = ChatMessage(
          id: '123',
          text: 'Check this out',
          createdAt: DateTime(2025, 11, 30, 10, 30),
          isUser: true,
          userId: 'user1',
          userName: 'John',
          conversationId: 'conv1',
          imageUrl: 'https://example.com/image.jpg',
          type: MessageType.image,
          isBot: false,
        );

        final json = message.toJson();

        expect(json['imageUrl'], 'https://example.com/image.jpg');
        expect(json['type'], 'image');
      });

      test('should serialize message with clientMessageId', () {
        final message = ChatMessage(
          id: '123',
          text: 'Hello',
          createdAt: DateTime(2025, 11, 30, 10, 30),
          isUser: true,
          userId: 'user1',
          userName: 'John',
          conversationId: 'conv1',
          clientMessageId: 'client-123',
          isBot: false,
          type: MessageType.text,
        );

        final json = message.toJson();

        expect(json['clientMessageId'], 'client-123');
      });
    });

    group('MessageType enum', () {
      test('should have text type', () {
        expect(MessageType.text, isA<MessageType>());
      });

      test('should have image type', () {
        expect(MessageType.image, isA<MessageType>());
      });
    });
  });
}
