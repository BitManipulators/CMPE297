import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter/foundation.dart';

class AppConfig {
  // Backend server URL
  static const String backendBaseUrl = 'http://localhost:8001';
  static const String websocketBaseUrl = 'ws://localhost:8001';

  // Google OAuth Client ID
  static String? get googleClientId {
    final clientId = dotenv.env['GOOGLE_CLIENT_ID'];
    return clientId;
  }
}

