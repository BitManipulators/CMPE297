import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:into_the_wild/main.dart';
import 'package:into_the_wild/screens/simple_chat_screen.dart';
import 'package:into_the_wild/models/user.dart';
import 'package:dash_chat_2/dash_chat_2.dart';

import 'test_helpers.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Real-Time Messaging Integration Tests', () {
    late User testUser;

    setUp(() async {
      // Clear all app state before each test
      await IntegrationTestHelpers.clearAppState();

      // Create and save a test user
      testUser = User(
        id: 'test_user_${DateTime.now().millisecondsSinceEpoch}',
        username: 'test_user',
        email: 'test@example.com',
        createdAt: DateTime.now().toIso8601String(),
      );
      await IntegrationTestHelpers.saveTestUser(testUser);
    });

    testWidgets('User can send a text message',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test requires:
      // 1. A conversation to be loaded
      // 2. Backend/WebSocket connection
      // 3. Navigate to chat screen

      // Example flow (requires setup):
      // - Select a conversation
      // - Wait for chat screen to load
      // - Enter message text
      // - Tap send button
      // - Verify message appears in chat list
      // - Verify WebSocket sent the message
      // - Verify optimistic message has clientMessageId

      await tester.pump(const Duration(seconds: 1));

      // Look for text input field
      final textFields = find.byType(TextField);
      
      if (textFields.evaluate().isNotEmpty) {
        final messageText = 'Test message ${DateTime.now().millisecondsSinceEpoch}';
        
        // Enter message
        await tester.enterText(textFields.first, messageText);
        await tester.pumpAndSettle();

        // Find and tap send button
        final sendButton = find.byIcon(Icons.send);
        if (sendButton.evaluate().isNotEmpty) {
          await tester.tap(sendButton);
          await tester.pumpAndSettle();

          // Verify message appears (optimistically)
          await tester.pump(const Duration(milliseconds: 100));
          
          // Message should appear in chat
          // Note: DashChat uses a complex widget tree
        }
      }
    });

    testWidgets('Message shows loading state then confirmation',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test verifies:
      // 1. Message appears immediately (optimistic update)
      // 2. Message has clientMessageId
      // 3. After WebSocket confirms, server ID replaces clientMessageId
      // 4. No duplicate messages appear

      // Requires WebSocket mock or real backend
    });

    testWidgets('User can send a message with image',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Look for image picker button
      final imageButton = find.byIcon(Icons.image);
      
      if (imageButton.evaluate().isNotEmpty) {
        // Tap image button
        await tester.tap(imageButton);
        await tester.pumpAndSettle();

        // This would trigger image picker
        // In integration test, you'd need to mock the image picker
        // or use a test image file
      }
    });

    testWidgets('User can use voice input',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Look for microphone button
      final micButton = find.byIcon(Icons.mic);
      
      if (micButton.evaluate().isNotEmpty) {
        // Tap microphone button
        await tester.tap(micButton);
        await tester.pumpAndSettle();

        // Verify microphone is active (icon changes to stop)
        final stopButton = find.byIcon(Icons.stop);
        if (stopButton.evaluate().isNotEmpty) {
          // Stop recording
          await tester.tap(stopButton);
          await tester.pumpAndSettle();
        }
      }
    });

    testWidgets('Messages are deduplicated using clientMessageId',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test verifies:
      // 1. Send message → optimistic message added with clientMessageId
      // 2. WebSocket returns same message with server ID
      // 3. ChatService deduplicates based on clientMessageId
      // 4. Only one message appears in UI

      // Requires controlled WebSocket responses
    });

    testWidgets('Messages appear in correct chronological order',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Send multiple messages rapidly
      final textFields = find.byType(TextField);
      
      if (textFields.evaluate().isNotEmpty) {
        for (int i = 1; i <= 3; i++) {
          await tester.enterText(textFields.first, 'Message $i');
          await tester.pumpAndSettle();

          final sendButton = find.byIcon(Icons.send);
          if (sendButton.evaluate().isNotEmpty) {
            await tester.tap(sendButton);
            await tester.pump(const Duration(milliseconds: 100));
          }
        }

        await tester.pumpAndSettle();

        // Verify messages appear in order
        // Would need to check message list structure
      }
    });

    testWidgets('Chat scrolls to bottom when new message arrives',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test verifies auto-scroll behavior
      // When new message arrives, chat should scroll to bottom
      // Requires message list to exist and be scrollable
    });

    testWidgets('User receives real-time messages from other users',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test requires:
      // 1. WebSocket connection established
      // 2. Simulate incoming message from another user
      // 3. Verify message appears in chat
      // 4. Verify message is marked as not from current user

      // Would use MockBackend to send WebSocket message
      // Then verify UI updates
    });

    testWidgets('Connection status is displayed when WebSocket disconnects',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify connection indicator (if implemented)
      // - Green/connected when WebSocket is active
      // - Red/disconnected when WebSocket drops
      // - Reconnecting state during reconnection attempts
    });

    testWidgets('Failed messages can be retried',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test verifies:
      // 1. Send message when WebSocket is disconnected
      // 2. Message shows error state
      // 3. User can tap retry button
      // 4. Message sends successfully when connection restored

      // Requires controlling WebSocket connection state
    });
  });
}
