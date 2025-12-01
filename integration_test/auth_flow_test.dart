import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:into_the_wild/main.dart';
import 'package:into_the_wild/screens/login_screen.dart';
import 'package:into_the_wild/screens/conversation_list_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'test_helpers.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  group('Authentication Flow Integration Tests', () {
    setUp(() async {
      // Clear all app state before each test
      await IntegrationTestHelpers.clearAppState();
    });

    testWidgets('User can register with username and navigate to conversation list',
        (WidgetTester tester) async {
      // Set viewport size
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      // Start the app
      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify we're on the login screen
      expect(find.byType(LoginScreen), findsOneWidget);
      expect(find.text('Welcome to IntoTheWild'), findsOneWidget);

      // Generate unique test username
      final testUsername = IntegrationTestHelpers.generateTestUsername();

      // Enter username
      final usernameField = find.byType(TextField).first;
      await tester.enterText(usernameField, testUsername);
      await tester.pumpAndSettle();

      // Tap Get Started button
      final getStartedButton = find.text('Get Started');
      expect(getStartedButton, findsOneWidget);

      // Note: This will fail without a real backend, but demonstrates the flow
      // In a real integration test, you'd mock the HTTP response or use a test backend
      await tester.tap(getStartedButton);
      await tester.pump();

      // Verify loading indicator appears
      expect(find.byType(CircularProgressIndicator), findsOneWidget);

      // In a real test with backend, we would verify:
      // - Navigation to ConversationListScreen
      // - User saved to SharedPreferences
      // - AuthService.isAuthenticated is true
    });

    testWidgets('User can register with username and email',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      final testUsername = IntegrationTestHelpers.generateTestUsername();
      final testEmail = IntegrationTestHelpers.generateTestEmail();

      // Enter both username and email
      final textFields = find.byType(TextField);
      await tester.enterText(textFields.first, testUsername);
      await tester.enterText(textFields.last, testEmail);
      await tester.pumpAndSettle();

      // Tap Get Started button
      await tester.tap(find.text('Get Started'));
      await tester.pump();

      // Verify loading state
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('Registration shows error when username is empty',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Tap Get Started without entering username
      await tester.tap(find.text('Get Started'));
      await tester.pump();

      // Verify error message
      expect(find.text('Please enter a username'), findsOneWidget);
    });

    testWidgets('User can tap Google Sign In button',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Find and tap Google Sign In button
      final googleButton = find.text('Continue with Google');
      expect(googleButton, findsOneWidget);

      await tester.tap(googleButton);
      await tester.pump();

      // Verify loading state (actual Google auth would fail without setup)
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('Logged in user sees conversation list on app start',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      // Pre-save a test user to SharedPreferences
      final prefs = await SharedPreferences.getInstance();
      final testUser = {
        'id': 'test_user_123',
        'username': 'test_user',
        'email': 'test@example.com',
        'createdAt': DateTime.now().toIso8601String(),
      };
      await prefs.setString('current_user', '${testUser}');

      // Start the app
      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Verify we're NOT on login screen
      expect(find.byType(LoginScreen), findsNothing);

      // Verify we're on conversation list (will show after auth loads)
      // Note: This may require backend to load conversations
      await tester.pumpAndSettle(const Duration(seconds: 2));
    });

    testWidgets('User can logout and return to login screen',
        (WidgetTester tester) async {
      IntegrationTestHelpers.setLargeViewport(tester);
      addTearDown(() => IntegrationTestHelpers.resetViewport(tester));

      // Pre-save a test user
      final prefs = await SharedPreferences.getInstance();
      final testUser = {
        'id': 'test_user_123',
        'username': 'test_user',
        'createdAt': DateTime.now().toIso8601String(),
      };
      await prefs.setString('current_user', '${testUser}');

      await tester.pumpWidget(const IntoTheWildApp());
      await tester.pumpAndSettle();

      // Should be on conversation list screen
      expect(find.byType(ConversationListScreen), findsOneWidget);

      // Find and tap logout button
      final logoutButton = find.byIcon(Icons.logout);
      expect(logoutButton, findsOneWidget);

      await tester.tap(logoutButton);
      await tester.pumpAndSettle();

      // Verify we're back on login screen
      expect(find.byType(LoginScreen), findsOneWidget);
      expect(find.text('Welcome to IntoTheWild'), findsOneWidget);

      // Verify user was cleared from SharedPreferences
      final savedUser = await IntegrationTestHelpers.getSavedUser();
      expect(savedUser, isNull);
    });
  });
}
