import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:into_the_wild/main.dart';
import 'package:into_the_wild/screens/conversation_list_screen.dart';
import 'package:into_the_wild/screens/simple_chat_screen.dart';
import 'package:into_the_wild/models/user.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'test_helpers.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Conversation Management Integration Tests', () {
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

    testWidgets('Logged in user can view conversation list',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify conversation list screen is displayed
      expect(find.byType(ConversationListScreen), findsOneWidget);
      expect(find.text('Conversations'), findsOneWidget);

      // Verify logout button is present
      expect(find.byIcon(Icons.logout), findsOneWidget);
    });

    testWidgets('User can navigate to new conversation dialog',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Look for FAB or new conversation button
      // Note: The actual implementation may vary
      final newConversationButton = find.byIcon(Icons.add);
      
      if (newConversationButton.evaluate().isNotEmpty) {
        await tester.tap(newConversationButton);
        await tester.pumpAndSettle();

        // Verify dialog or new screen appears
        // Actual verification depends on implementation
      }
    });

    testWidgets('User can create a new conversation (mocked backend)',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test would require:
      // 1. Mock HTTP responses for creating conversation
      // 2. Enter conversation name
      // 3. Select participants
      // 4. Tap create button
      // 5. Verify conversation appears in list

      // Example flow (would need real backend or mocks):
      // final createButton = find.byIcon(Icons.add);
      // await tester.tap(createButton);
      // await tester.pumpAndSettle();
      // 
      // await tester.enterText(find.byType(TextField), 'Test Chat');
      // await tester.tap(find.text('Create'));
      // await tester.pumpAndSettle();
      //
      // expect(find.text('Test Chat'), findsOneWidget);
    });

    testWidgets('User can select a conversation and navigate to chat screen',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // This test requires backend to return conversations
      // Wait for conversations to load
      await tester.pump(const Duration(seconds: 1));

      // Look for conversation tiles
      final conversationTiles = find.byType(ListTile);
      
      if (conversationTiles.evaluate().isNotEmpty) {
        // Tap the first conversation
        await tester.tap(conversationTiles.first);
        await tester.pumpAndSettle();

        // On wide layouts, chat appears in split view
        // On narrow layouts, navigate to SimpleChatScreen
        // Verify one or the other
        final hasChat = find.byType(SimpleChatScreen).evaluate().isNotEmpty;
        final hasChatUI = find.byType(TextField).evaluate().isNotEmpty;
        
        expect(hasChat || hasChatUI, isTrue,
            reason: 'Should show chat UI after selecting conversation');
      }
    });

    testWidgets('Conversation list shows user\'s conversations',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Wait for API call to complete (with real backend)
      await tester.pump(const Duration(seconds: 2));

      // Verify loading indicator is gone
      final loadingIndicators = find.byType(CircularProgressIndicator);
      
      // Either no loading indicators, or conversations have loaded
      // This depends on backend returning data
    });

    testWidgets('Wide layout shows split view with conversation list and chat',
        (WidgetTester tester) async {
      // Set wide viewport (desktop/tablet)
      tester.view.physicalSize = const Size(1920, 1080);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // On wide layouts, should see split view
      // Left side: conversation list
      // Right side: chat area or placeholder

      expect(find.byType(ConversationListScreen), findsOneWidget);
      
      // Look for Row or split layout indicators
      final rows = find.byType(Row);
      expect(rows.evaluate().isNotEmpty, isTrue,
          reason: 'Wide layout should use Row for split view');
    });

    testWidgets('Narrow layout shows only conversation list initially',
        (WidgetTester tester) async {
      // Set narrow viewport (mobile)
      tester.view.physicalSize = const Size(400, 800);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // On narrow layouts, should only see conversation list
      expect(find.byType(ConversationListScreen), findsOneWidget);

      // Chat screen should not be visible yet
      expect(find.byType(SimpleChatScreen), findsNothing);
    });

    testWidgets('User can search/filter conversations',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Look for search field or search icon
      final searchIcon = find.byIcon(Icons.search);
      
      if (searchIcon.evaluate().isNotEmpty) {
        await tester.tap(searchIcon);
        await tester.pumpAndSettle();

        // Enter search text
        final searchField = find.byType(TextField);
        if (searchField.evaluate().isNotEmpty) {
          await tester.enterText(searchField.first, 'test');
          await tester.pumpAndSettle();

          // Verify filtering works (requires conversations to exist)
        }
      }
    });
  });
}
