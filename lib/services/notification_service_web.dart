// Web-specific notification implementation
import 'dart:async';
import 'dart:js' as js;

class WebNotificationHelper {
  /// Show a browser notification
  static Future<bool> showNotification({
    required String title,
    required String body,
    required String conversationId,
    required Function(String) onTap,
  }) async {
    try {
      // Access Notification via JS context
      final Notification = js.context['Notification'];
      if (Notification == null) {
        return false;
      }

      // Check current permission
      final permission = Notification['permission'] as String?;

      if (permission == 'denied') {
        return false;
      }

      // Request permission if needed
      String finalPermission = permission ?? 'default';
      if (permission == 'default') {
        final permissionPromise = Notification.callMethod('requestPermission', []);
        finalPermission = await _promiseToFuture(permissionPromise);
        if (finalPermission != 'granted') {
          return false;
        }
      }

      // Create notification options
      final options = js.JsObject.jsify({
        'body': body,
        'icon': '/favicon.png',
        'tag': conversationId, // Group notifications by conversation
      });

      // Create and show notification
      final notification = js.JsObject(Notification, [title, options]);

      // Handle click - only trigger navigation when user clicks
      notification['onclick'] = js.allowInterop((event) {
        onTap(conversationId);
        notification.callMethod('close', []);
      });

      // Auto-close after 5 seconds
      Future.delayed(const Duration(seconds: 5), () {
        try {
          notification.callMethod('close', []);
        } catch (e) {
          // Ignore
        }
      });

      return true;
    } catch (e) {
      return false;
    }
  }

  /// Convert JS Promise to Future
  static Future<String> _promiseToFuture(js.JsObject promise) async {
    final completer = Completer<String>();
    promise.callMethod('then', [
      js.allowInterop((result) {
        completer.complete(result.toString());
      }),
      js.allowInterop((error) {
        completer.complete('denied');
      }),
    ]);
    return completer.future;
  }

  /// Get current notification permission
  static Future<String?> getPermission() async {
    try {
      final Notification = js.context['Notification'];
      if (Notification != null) {
        return Notification['permission'] as String?;
      }
    } catch (e) {
      // Ignore
    }
    return null;
  }

  /// Request notification permission
  static Future<String> requestPermission() async {
    try {
      final Notification = js.context['Notification'];
      if (Notification != null) {
        final promise = Notification.callMethod('requestPermission', []);
        return await _promiseToFuture(promise);
      }
    } catch (e) {
      // Ignore
    }
    return 'denied';
  }
}

