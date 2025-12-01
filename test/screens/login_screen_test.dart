import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:mockito/mockito.dart';
import 'package:into_the_wild/screens/login_screen.dart';
import 'package:into_the_wild/services/auth_service.dart';

import '../mocks.mocks.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  
  group('LoginScreen Widget Tests', () {
    late MockAuthService mockAuthService;

    setUp(() {
      mockAuthService = MockAuthService();
      
      // Set up default behavior
      when(mockAuthService.isAuthenticated).thenReturn(false);
      when(mockAuthService.currentUser).thenReturn(null);
      when(mockAuthService.addListener(any)).thenReturn(null);
      when(mockAuthService.removeListener(any)).thenReturn(null);
    });

    Widget createLoginScreen() {
      return ChangeNotifierProvider<AuthService>.value(
        value: mockAuthService,
        child: const MaterialApp(
          home: LoginScreen(),
        ),
      );
    }

    testWidgets('should display username and email text fields',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      await tester.pumpWidget(createLoginScreen());

      expect(find.byType(TextField), findsNWidgets(2));
      expect(find.text('Username'), findsOneWidget);
      expect(find.text('Email (optional)'), findsOneWidget);
    });

    testWidgets('should display Get Started and Google Sign In buttons',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      await tester.pumpWidget(createLoginScreen());

      expect(find.text('Get Started'), findsOneWidget);
      expect(find.text('Continue with Google'), findsOneWidget);
    });

    testWidgets('should show error when username is empty',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      await tester.pumpWidget(createLoginScreen());

      // Find and tap the Get Started button without entering username
      final registerButton = find.text('Get Started');
      await tester.tap(registerButton);
      await tester.pump();

      // Should show error
      expect(find.text('Please enter a username'), findsOneWidget);
    });

    testWidgets('should call register when valid username is entered',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      when(mockAuthService.register(any, email: anyNamed('email')))
          .thenAnswer((_) async => throw Exception('Mock not implemented'));

      await tester.pumpWidget(createLoginScreen());

      // Enter username
      await tester.enterText(find.byType(TextField).first, 'john_doe');

      // Tap Get Started button
      final registerButton = find.text('Get Started');
      await tester.tap(registerButton);
      await tester.pump();

      // Should attempt to register
      verify(mockAuthService.register('john_doe', email: null)).called(1);
    });

    testWidgets('should call register with email when both are entered',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      when(mockAuthService.register(any, email: anyNamed('email')))
          .thenAnswer((_) async => throw Exception('Mock not implemented'));

      await tester.pumpWidget(createLoginScreen());

      // Enter username and email
      final textFields = find.byType(TextField);
      await tester.enterText(textFields.at(0), 'john_doe');
      await tester.enterText(textFields.at(1), 'john@example.com');

      // Tap Get Started button
      final registerButton = find.text('Get Started');
      await tester.tap(registerButton);
      await tester.pump();

      // Should attempt to register with email
      verify(mockAuthService.register('john_doe', email: 'john@example.com'))
          .called(1);
    });

    testWidgets('should call Google sign in when button is tapped',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      when(mockAuthService.signInWithGoogle())
          .thenAnswer((_) async => throw Exception('Mock not implemented'));

      await tester.pumpWidget(createLoginScreen());

      // Find and tap the Continue with Google button
      final googleButton = find.text('Continue with Google');
      await tester.tap(googleButton);
      await tester.pump();

      // Should attempt Google sign in
      verify(mockAuthService.signInWithGoogle()).called(1);
    });

    testWidgets('should show loading indicator during registration',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      // Mock register to delay for a bit
      var completerCalled = false;
      when(mockAuthService.register(any, email: anyNamed('email')))
          .thenAnswer((_) async {
        completerCalled = true;
        await Future.delayed(Duration(milliseconds: 100));
        throw Exception('Mock');
      });

      await tester.pumpWidget(createLoginScreen());

      // Enter username
      await tester.enterText(find.byType(TextField).first, 'john_doe');

      // Tap Get Started button
      final registerButton = find.text('Get Started');
      await tester.tap(registerButton);
      await tester.pump();

      // Should show loading indicator
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(completerCalled, isTrue);
      
      // Clean up - wait for the future to complete
      await tester.pumpAndSettle();
    });

    testWidgets('should display error message on registration failure',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      when(mockAuthService.register(any, email: anyNamed('email')))
          .thenThrow(Exception('Network error'));

      await tester.pumpWidget(createLoginScreen());

      // Enter username
      await tester.enterText(find.byType(TextField).first, 'john_doe');

      // Tap Get Started button
      final registerButton = find.text('Get Started');
      await tester.tap(registerButton);
      await tester.pumpAndSettle();

      // Should display error message
      expect(find.textContaining('error', findRichText: true), findsOneWidget);
    });

    testWidgets('should display error message on Google sign in failure',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      when(mockAuthService.signInWithGoogle())
          .thenThrow(Exception('Google sign in failed'));

      await tester.pumpWidget(createLoginScreen());

      // Tap Continue with Google button
      final googleButton = find.text('Continue with Google');
      await tester.tap(googleButton);
      await tester.pump(); // Trigger the frame that shows the SnackBar
      await tester.pump(const Duration(milliseconds: 100)); // Wait for SnackBar animation

      // Should display error message in SnackBar
      expect(find.text('Error: Exception: Google sign in failed'), findsOneWidget);
    });

    testWidgets('should disable buttons during loading',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 2000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.reset);
      
      when(mockAuthService.register(any, email: anyNamed('email')))
          .thenAnswer((_) async {
        await Future.delayed(Duration(milliseconds: 100));
        throw Exception('Mock');
      });

      await tester.pumpWidget(createLoginScreen());

      // Enter username
      await tester.enterText(find.byType(TextField).first, 'john_doe');

      // Tap Get Started button
      final registerButton = find.text('Get Started');
      await tester.tap(registerButton);
      await tester.pump();

      // During loading, the button shows a CircularProgressIndicator instead of text
      // This means the button callback is null (disabled)
      final registerBtn = tester.widget<ElevatedButton>(
        find.byType(ElevatedButton).first,
      );
      expect(registerBtn.onPressed, isNull);
      
      // Clean up
      await tester.pumpAndSettle();
    });
  });
}
