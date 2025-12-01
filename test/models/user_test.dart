import 'package:flutter_test/flutter_test.dart';
import 'package:into_the_wild/models/user.dart';

void main() {
  group('User', () {
    group('fromJson', () {
      test('should parse user with all fields', () {
        final json = {
          'id': 'user1',
          'username': 'john_doe',
          'email': 'john@example.com',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'googleId': 'google123',
          'picture': 'https://example.com/profile.jpg',
          'lastLoginAt': '2025-11-30T12:00:00.000Z',
        };

        final user = User.fromJson(json);

        expect(user.id, 'user1');
        expect(user.username, 'john_doe');
        expect(user.email, 'john@example.com');
        expect(user.createdAt, '2025-11-30T10:30:00.000Z');
        expect(user.googleId, 'google123');
        expect(user.picture, 'https://example.com/profile.jpg');
        expect(user.lastLoginAt, '2025-11-30T12:00:00.000Z');
      });

      test('should parse user with only required fields', () {
        final json = {
          'id': 'user1',
          'username': 'john_doe',
        };

        final user = User.fromJson(json);

        expect(user.id, 'user1');
        expect(user.username, 'john_doe');
        expect(user.email, isNull);
        expect(user.createdAt, isNull);
        expect(user.googleId, isNull);
        expect(user.picture, isNull);
        expect(user.lastLoginAt, isNull);
      });

      test('should handle null email', () {
        final json = {
          'id': 'user1',
          'username': 'john_doe',
          'email': null,
        };

        final user = User.fromJson(json);

        expect(user.email, isNull);
      });

      test('should handle null createdAt', () {
        final json = {
          'id': 'user1',
          'username': 'john_doe',
          'createdAt': null,
        };

        final user = User.fromJson(json);

        expect(user.createdAt, isNull);
      });

      test('should handle null googleId', () {
        final json = {
          'id': 'user1',
          'username': 'john_doe',
          'googleId': null,
        };

        final user = User.fromJson(json);

        expect(user.googleId, isNull);
      });

      test('should handle null picture', () {
        final json = {
          'id': 'user1',
          'username': 'john_doe',
          'picture': null,
        };

        final user = User.fromJson(json);

        expect(user.picture, isNull);
      });

      test('should handle null lastLoginAt', () {
        final json = {
          'id': 'user1',
          'username': 'john_doe',
          'lastLoginAt': null,
        };

        final user = User.fromJson(json);

        expect(user.lastLoginAt, isNull);
      });

      test('should parse user from Google OAuth response', () {
        final json = {
          'id': 'user1',
          'username': 'john_doe',
          'email': 'john@gmail.com',
          'googleId': 'google123',
          'picture': 'https://lh3.googleusercontent.com/a/profile.jpg',
          'createdAt': '2025-11-30T10:30:00.000Z',
          'lastLoginAt': '2025-11-30T12:00:00.000Z',
        };

        final user = User.fromJson(json);

        expect(user.googleId, isNotNull);
        expect(user.email, contains('@gmail.com'));
        expect(user.picture, contains('googleusercontent.com'));
      });

      test('should parse user from username registration', () {
        final json = {
          'id': 'user1',
          'username': 'john_doe',
          'createdAt': '2025-11-30T10:30:00.000Z',
        };

        final user = User.fromJson(json);

        expect(user.googleId, isNull);
        expect(user.email, isNull);
        expect(user.picture, isNull);
      });
    });

    group('toJson', () {
      test('should serialize user to JSON with all fields', () {
        final user = User(
          id: 'user1',
          username: 'john_doe',
          email: 'john@example.com',
          createdAt: '2025-11-30T10:30:00.000Z',
          googleId: 'google123',
          picture: 'https://example.com/profile.jpg',
          lastLoginAt: '2025-11-30T12:00:00.000Z',
        );

        final json = user.toJson();

        expect(json['id'], 'user1');
        expect(json['username'], 'john_doe');
        expect(json['email'], 'john@example.com');
        expect(json['createdAt'], '2025-11-30T10:30:00.000Z');
        expect(json['googleId'], 'google123');
        expect(json['picture'], 'https://example.com/profile.jpg');
        expect(json['lastLoginAt'], '2025-11-30T12:00:00.000Z');
      });

      test('should serialize user with only required fields', () {
        final user = User(
          id: 'user1',
          username: 'john_doe',
        );

        final json = user.toJson();

        expect(json['id'], 'user1');
        expect(json['username'], 'john_doe');
        expect(json['email'], isNull);
        expect(json['createdAt'], isNull);
        expect(json['googleId'], isNull);
        expect(json['picture'], isNull);
        expect(json['lastLoginAt'], isNull);
      });

      test('should serialize and deserialize consistently', () {
        final original = User(
          id: 'user1',
          username: 'john_doe',
          email: 'john@example.com',
          createdAt: '2025-11-30T10:30:00.000Z',
          googleId: 'google123',
          picture: 'https://example.com/profile.jpg',
          lastLoginAt: '2025-11-30T12:00:00.000Z',
        );

        final json = original.toJson();
        final deserialized = User.fromJson(json);

        expect(deserialized.id, original.id);
        expect(deserialized.username, original.username);
        expect(deserialized.email, original.email);
        expect(deserialized.createdAt, original.createdAt);
        expect(deserialized.googleId, original.googleId);
        expect(deserialized.picture, original.picture);
        expect(deserialized.lastLoginAt, original.lastLoginAt);
      });
    });
  });
}
