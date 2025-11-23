// Stub file for non-web platforms
class WebNotificationHelper {
  static Future<bool> showNotification({
    required String title,
    required String body,
    required String conversationId,
    required Function(String) onTap,
  }) async {
    return false;
  }

  static Future<String?> getPermission() async {
    return null;
  }

  static Future<String> requestPermission() async {
    return 'denied';
  }
}

