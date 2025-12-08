import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'platform_helper.dart' if (dart.library.html) 'platform_helper_stub.dart' show isAndroidPlatform;

class AppConfig {
  // Backend server URL
  // Use production URL for Android devices
  // Use localhost for web and other platforms
  static String get backendBaseUrl {
    return 'https://iotsmarthome.org/backend';
  }

  static String get websocketBaseUrl {
    return 'wss://iotsmarthome.org/backend';
  }

  // Google OAuth Client ID
  static String? get googleClientId {
    final clientId = dotenv.env['GOOGLE_CLIENT_ID'];
    return clientId;
  }
}
