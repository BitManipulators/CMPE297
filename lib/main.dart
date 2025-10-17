import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'screens/chat_screen.dart';
import 'services/permission_service.dart';
import 'services/chat_service.dart';
import 'services/ai_model_interface.dart';
import 'services/ai_model_service_web.dart';
import 'services/ai_model_service_android.dart';

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
        Provider<AIModelInterface>(create: (_) {
          if (kIsWeb) {
            return AIModelServiceWeb();
          } else {
            return AIModelServiceAndroid();
          }
        }),
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
        home: const ChatScreen(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}
