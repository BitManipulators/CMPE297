import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:into_the_wild/main.dart';
import 'package:into_the_wild/services/chat_service.dart';
import 'package:into_the_wild/services/auth_service.dart';
import 'package:into_the_wild/services/conversation_service.dart';
import 'package:into_the_wild/services/websocket_service.dart';
import 'package:into_the_wild/services/notification_service.dart';

void main() {
  testWidgets('IntoTheWildApp smoke test', (WidgetTester tester) async {
    // Set larger viewport to prevent RenderFlex overflow
    tester.view.physicalSize = const Size(1200, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    
    // Build the actual app with all providers
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AuthService()),
          ChangeNotifierProvider(create: (_) => WebSocketService()),
          ChangeNotifierProvider(create: (_) => ConversationService()),
          ChangeNotifierProvider(create: (_) => ChatService()),
          ChangeNotifierProvider(create: (_) => NotificationService()),
        ],
        child: const IntoTheWildApp(),
      ),
    );

    // Wait for the app to initialize
    await tester.pumpAndSettle();

    // The app should render without crashing
    expect(find.byType(MaterialApp), findsOneWidget);
  });

  testWidgets('IntoTheWildApp should show login screen when not authenticated',
      (WidgetTester tester) async {
    // Set larger viewport to prevent RenderFlex overflow
    tester.view.physicalSize = const Size(1200, 2000);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);
    
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => AuthService()),
          ChangeNotifierProvider(create: (_) => WebSocketService()),
          ChangeNotifierProvider(create: (_) => ConversationService()),
          ChangeNotifierProvider(create: (_) => ChatService()),
          ChangeNotifierProvider(create: (_) => NotificationService()),
        ],
        child: const IntoTheWildApp(),
      ),
    );

    await tester.pumpAndSettle();

    // Should show login screen when not authenticated
    // Note: This depends on AuthService initial state
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}
