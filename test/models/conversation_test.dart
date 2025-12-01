import 'package:flutter_test/flutter_test.dart';
import 'package:into_the_wild/models/conversation.dart';

void main() {
  group('Conversation', () {
    group('fromJson', () {
      test('should parse conversation with all fields', () {
        final json = {
          'id': 'conv1',
          'name': 'Test Group',
          'type': 'group',
          'participants': ['user1', 'user2', 'user3'],
          'createdAt': '2025-11-30T10:30:00.000Z',
          'hasBot': true,
        };

        final conversation = Conversation.fromJson(json);

        expect(conversation.id, 'conv1');
        expect(conversation.name, 'Test Group');
        expect(conversation.type, 'group');
        expect(conversation.participants, ['user1', 'user2', 'user3']);
        expect(conversation.createdAt, '2025-11-30T10:30:00.000Z');
        expect(conversation.hasBot, isTrue);
      });

      test('should parse conversation without name', () {
        final json = {
          'id': 'conv1',
          'type': 'direct',
          'participants': ['user1', 'user2'],
          'createdAt': '2025-11-30T10:30:00.000Z',
        };

        final conversation = Conversation.fromJson(json);

        expect(conversation.id, 'conv1');
        expect(conversation.name, isNull);
        expect(conversation.type, 'direct');
      });

      test('should default hasBot to false when not provided', () {
        final json = {
          'id': 'conv1',
          'type': 'direct',
          'participants': ['user1', 'user2'],
          'createdAt': '2025-11-30T10:30:00.000Z',
        };

        final conversation = Conversation.fromJson(json);

        expect(conversation.hasBot, isFalse);
      });

      test('should parse empty participants list', () {
        final json = {
          'id': 'conv1',
          'type': 'group',
          'participants': [],
          'createdAt': '2025-11-30T10:30:00.000Z',
        };

        final conversation = Conversation.fromJson(json);

        expect(conversation.participants, isEmpty);
      });

      test('should parse conversation with single participant', () {
        final json = {
          'id': 'conv1',
          'type': 'direct',
          'participants': ['user1'],
          'createdAt': '2025-11-30T10:30:00.000Z',
        };

        final conversation = Conversation.fromJson(json);

        expect(conversation.participants, hasLength(1));
        expect(conversation.participants[0], 'user1');
      });

      test('should parse conversation with multiple types', () {
        final jsonDirect = {
          'id': 'conv1',
          'type': 'direct',
          'participants': ['user1', 'user2'],
          'createdAt': '2025-11-30T10:30:00.000Z',
        };

        final jsonGroup = {
          'id': 'conv2',
          'type': 'group',
          'participants': ['user1', 'user2', 'user3'],
          'createdAt': '2025-11-30T10:30:00.000Z',
        };

        final direct = Conversation.fromJson(jsonDirect);
        final group = Conversation.fromJson(jsonGroup);

        expect(direct.type, 'direct');
        expect(group.type, 'group');
      });
    });

    group('toJson', () {
      test('should serialize conversation to JSON', () {
        final conversation = Conversation(
          id: 'conv1',
          name: 'Test Group',
          type: 'group',
          participants: ['user1', 'user2', 'user3'],
          createdAt: '2025-11-30T10:30:00.000Z',
          hasBot: true,
        );

        final json = conversation.toJson();

        expect(json['id'], 'conv1');
        expect(json['name'], 'Test Group');
        expect(json['type'], 'group');
        expect(json['participants'], ['user1', 'user2', 'user3']);
        expect(json['createdAt'], '2025-11-30T10:30:00.000Z');
        expect(json['hasBot'], isTrue);
      });

      test('should serialize conversation without name', () {
        final conversation = Conversation(
          id: 'conv1',
          type: 'direct',
          participants: ['user1', 'user2'],
          createdAt: '2025-11-30T10:30:00.000Z',
          hasBot: false,
        );

        final json = conversation.toJson();

        expect(json['id'], 'conv1');
        expect(json['name'], isNull);
        expect(json['type'], 'direct');
        expect(json['hasBot'], isFalse);
      });

      test('should serialize empty participants list', () {
        final conversation = Conversation(
          id: 'conv1',
          type: 'group',
          participants: [],
          createdAt: '2025-11-30T10:30:00.000Z',
          hasBot: false,
        );

        final json = conversation.toJson();

        expect(json['participants'], isEmpty);
      });

      test('should serialize and deserialize consistently', () {
        final original = Conversation(
          id: 'conv1',
          name: 'Test Group',
          type: 'group',
          participants: ['user1', 'user2', 'user3'],
          createdAt: '2025-11-30T10:30:00.000Z',
          hasBot: true,
        );

        final json = original.toJson();
        final deserialized = Conversation.fromJson(json);

        expect(deserialized.id, original.id);
        expect(deserialized.name, original.name);
        expect(deserialized.type, original.type);
        expect(deserialized.participants, original.participants);
        expect(deserialized.hasBot, original.hasBot);
      });
    });
  });
}
