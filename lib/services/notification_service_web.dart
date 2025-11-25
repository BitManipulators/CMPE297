// Web-specific notification implementation
import 'dart:async';
import 'dart:js' as js;
import 'dart:js_util' as js_util;

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

  /// Update badge count using Badge API (shows count on app icon)
  static void updateBadge(int count) {
    try {
      // Use eval to safely call Badge API (Chrome, Edge, Opera support)
      // This avoids issues with JavaScript interop for newer APIs
      if (count > 0) {
        // Show badge with count
        js.context.callMethod('eval', [
          'if (navigator.setAppBadge) { navigator.setAppBadge($count).catch(() => {}); }'
        ]);
      } else {
        // Clear badge
        js.context.callMethod('eval', [
          'if (navigator.clearAppBadge) { navigator.clearAppBadge().catch(() => {}); }'
        ]);
      }
    } catch (e) {
      // Badge API not supported or error occurred
      // This is fine, not all browsers support it
    }
  }

  /// Update document title with unread count (like WhatsApp)
  static void updateDocumentTitle(int count, String originalTitle) {
    try {
      final document = js.context['document'];
      if (document != null) {
        if (count > 0) {
          document['title'] = '($count) $originalTitle';
        } else {
          document['title'] = originalTitle;
        }
      }
    } catch (e) {
      // Error updating title
    }
  }

  /// Get current document title
  static String? getDocumentTitle() {
    try {
      final document = js.context['document'];
      if (document != null) {
        return document['title'] as String?;
      }
    } catch (e) {
      // Error getting title
    }
    return null;
  }
}

