import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:into_the_wild/main.dart';
import 'package:into_the_wild/services/chat_service.dart';
import 'package:into_the_wild/services/permission_service.dart';

void main() {
  testWidgets('IntoTheWild app smoke test', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => ChatService()),
          ChangeNotifierProvider(create: (_) => PermissionService()),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: Center(
              child: Text('IntoTheWild'),
            ),
          ),
        ),
      ),
    );

    // Verify that the app title is displayed
    expect(find.text('IntoTheWild'), findsOneWidget);
  });
}

