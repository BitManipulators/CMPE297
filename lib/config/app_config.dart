import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'platform_helper.dart' if (dart.library.html) 'platform_helper_stub.dart' show isAndroidPlatform;

class AppConfig {
  // Backend server URL
  // Use production URL for Android devices
  // Use localhost for web and other platforms
  static String get backendBaseUrl {
    // On web, always use localhost
    if (kIsWeb) {
      return 'http://localhost:8001';
    }
    // On mobile platforms, check if Android
    if (isAndroidPlatform()) {
      return 'http://10.0.2.2:8001';
    }
    return 'http://localhost:8001';
  }

  static String get websocketBaseUrl {
    // On web, always use localhost
    if (kIsWeb) {
      return 'ws://localhost:8001';
    }
    // On mobile platforms, check if Android
    if (isAndroidPlatform()) {
      return 'ws://10.0.2.2:8001';
    }
    return 'ws://localhost:8001';
  }

  // Google OAuth Client ID
  static String? get googleClientId {
    final clientId = dotenv.env['GOOGLE_CLIENT_ID'];
    return clientId;
  }
}
