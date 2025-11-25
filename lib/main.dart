import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'screens/login_screen.dart';
import 'screens/conversation_list_screen.dart';
import 'screens/simple_chat_screen.dart';
import 'services/chat_service.dart';
import 'services/auth_service.dart';
import 'services/websocket_service.dart';
import 'services/conversation_service.dart';
import 'services/notification_service.dart';
import 'dart:async';
import 'models/conversation.dart';
import 'package:flutter/foundation.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Load .env file
  try {
    await dotenv.load(fileName: ".env");
  } catch (e) {
    debugPrint('Warning: Could not load .env file: $e');
  }

  runApp(const IntoTheWildApp());
}

class IntoTheWildApp extends StatelessWidget {
  const IntoTheWildApp({super.key});

  // Global navigator key for handling notifications
  static final GlobalKey<NavigatorState> navigatorKey = GlobalKey<NavigatorState>();

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthService()),
        ChangeNotifierProvider(create: (_) => WebSocketService()),
        ChangeNotifierProvider(create: (_) => ConversationService()),
        ChangeNotifierProvider(create: (_) => ChatService()),
        ChangeNotifierProvider(create: (_) => NotificationService()),
      ],
      child: MaterialApp(
        navigatorKey: navigatorKey,
        title: 'IntoTheWild',
        theme: ThemeData(
          primarySwatch: Colors.green,
          visualDensity: VisualDensity.adaptivePlatformDensity,
          appBarTheme: const AppBarTheme(
            backgroundColor: Color(0xFF2E7D32),
            foregroundColor: Colors.white,
            elevation: 0,
          ),
        ),
        home: const AppInitializer(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}

class AppInitializer extends StatefulWidget {
  const AppInitializer({super.key});

  @override
  State<AppInitializer> createState() => _AppInitializerState();
}

class _AppInitializerState extends State<AppInitializer> {
  final NotificationService _notificationService = NotificationService();
  StreamSubscription? _notificationSubscription;

  @override
  void initState() {
    super.initState();
    _initializeNotifications();
  }

  Future<void> _initializeNotifications() async {
    await _notificationService.initialize();

    // Listen for notification taps
    _notificationSubscription = _notificationService.notificationResponseStream.listen(
      (response) {
        _handleNotificationTap(response.payload);
      },
    );
  }

  void _handleNotificationTap(String? conversationId) {
    if (conversationId == null) return;

    final navigator = IntoTheWildApp.navigatorKey.currentState;
    if (navigator == null) {
      debugPrint('Navigator not available for notification tap');
      return;
    }

    // Get services from the navigator context
    final context = navigator.context;
    final chatService = Provider.of<ChatService>(context, listen: false);
    final conversationService = Provider.of<ConversationService>(context, listen: false);

    // Find the conversation
    Conversation? conversation;
    try {
      conversation = conversationService.conversations.firstWhere(
        (c) => c.id == conversationId,
      );
    } catch (e) {
      // Conversation not found, try to fetch it
      debugPrint('Conversation not found in list, attempting to fetch: $conversationId');
      conversationService.getConversation(conversationId).then((conv) {
        if (conv != null) {
          conversationService.setCurrentConversation(conv);
          chatService.loadConversation(conversationId);

          navigator.push(
            MaterialPageRoute(
              builder: (_) => const SimpleChatScreen(),
            ),
          );
        }
      }).catchError((e) {
        debugPrint('Error fetching conversation: $e');
      });
      return;
    }

    // Load and open the conversation
    conversationService.setCurrentConversation(conversation);
    chatService.loadConversation(conversationId);

    // Navigate to chat screen if not already there
    navigator.push(
      MaterialPageRoute(
        builder: (_) => const SimpleChatScreen(),
      ),
    );
  }

  @override
  void dispose() {
    _notificationSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authService = context.watch<AuthService>();

    if (authService.isAuthenticated) {
      return const ConversationListScreen();
    } else {
      return const LoginScreen();
    }
  }
}
