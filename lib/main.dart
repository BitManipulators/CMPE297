import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'screens/simple_chat_screen.dart';
import 'services/permission_service.dart';
import 'services/chat_service.dart';

void main() {
  runApp(const IntoTheWildApp());
}

class IntoTheWildApp extends StatelessWidget {
  const IntoTheWildApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ChatService()),
        ChangeNotifierProvider(create: (_) => PermissionService()),
      ],
      child: MaterialApp(
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
        home: const SimpleChatScreen(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
