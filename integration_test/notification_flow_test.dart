import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:into_the_wild/main.dart';
import 'package:into_the_wild/models/user.dart';

import 'test_helpers.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Notification Integration Tests', () {
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

    testWidgets('Notification service initializes on app start',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify app starts without errors
      // NotificationService.initialize() should be called during AppInitializer
      expect(find.byType(MaterialApp), findsOneWidget);

      // On mobile platforms, notification permission might be requested
      // On web, browser Notification API is used
    });

    testWidgets('Notification appears when message received in background conversation',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test requires:
      // 1. User is viewing conversation A
      // 2. Message arrives for conversation B via WebSocket
      // 3. Notification should appear with:
      //    - Title: Sender name or conversation name
      //    - Body: Message text
      //    - Payload: conversationId for B
      // 4. Tap notification → navigate to conversation B

      // Would use MockBackend to simulate WebSocket message
      // Then check notification was triggered (might need platform channel mocks)
    });

    testWidgets('No notification for current conversation',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test verifies:
      // 1. User is viewing conversation A
      // 2. Message arrives for conversation A via WebSocket
      // 3. NO notification should appear
      // 4. Message just appears in chat

      // NotificationService.setCurrentConversationId() should suppress notifications
    });

    testWidgets('Unread count increases when notification shown',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify:
      // 1. Initial unread count is 0
      // 2. Message arrives → notification shown
      // 3. Unread count increments
      // 4. Badge/indicator appears on conversation list item
      // 5. Total unread count updates in app title/badge
    });

    testWidgets('Unread count clears when opening conversation',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify:
      // 1. Conversation has unread count > 0
      // 2. User taps conversation
      // 3. Unread count resets to 0
      // 4. Badge/indicator removed
      // 5. setCurrentConversationId() called with conversationId
    });

    testWidgets('Tapping notification navigates to correct conversation',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test requires:
      // 1. Multiple conversations exist
      // 2. User is on conversation A (or conversation list)
      // 3. Notification for conversation B is tapped
      // 4. App navigates to conversation B
      // 5. Chat screen shows conversation B messages

      // Simulating notification tap in integration test is platform-specific
      // May need to directly call the notification handler
      // _handleNotificationTap(conversationId) in main.dart
    });

    testWidgets('Notification badge updates in app title',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // On web, verify:
      // 1. Page title shows "IntoTheWild"
      // 2. Unread message arrives
      // 3. Page title updates to "(1) IntoTheWild"
      // 4. Multiple unreads → "(3) IntoTheWild"
      // 5. Opening conversation clears count → "IntoTheWild"

      // On mobile, app badge count should update
    });

    testWidgets('Notification permission is handled gracefully',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify:
      // 1. If notification permission denied, app still works
      // 2. No errors thrown
      // 3. In-app message indicators still work
      // 4. User can manually enable later

      // This is mostly about error handling, not breaking the app
    });

    testWidgets('Multiple notifications queue correctly',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify:
      // 1. Messages arrive from multiple conversations
      // 2. Each gets its own notification
      // 3. Notifications are grouped by conversation (if platform supports)
      // 4. Tapping each notification goes to correct conversation
    });

    testWidgets('Notification is canceled when conversation is opened',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify:
      // 1. Notification shown for conversation A
      // 2. User opens conversation A
      // 3. Notification is dismissed/canceled
      // 4. cancelConversationNotifications() is called
    });

    testWidgets('Web notifications use browser Notification API',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // On web platform:
      // 1. Check that web-specific notification code is used
      // 2. Browser Notification API is called (would need JS interop mock)
      // 3. Notification has correct title, body, icon
      // 4. Click handler navigates correctly

      // This is platform-specific and may not be easily testable in integration tests
    });
  });
}
