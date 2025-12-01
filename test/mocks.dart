import 'package:mockito/annotations.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'package:into_the_wild/services/websocket_service.dart';
import 'package:into_the_wild/services/auth_service.dart';
import 'package:into_the_wild/services/conversation_service.dart';
import 'package:into_the_wild/services/chat_service.dart';
import 'package:into_the_wild/services/notification_service.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:image_picker/image_picker.dart';

// Generate mocks with:
// dart run build_runner build --delete-conflicting-outputs

@GenerateMocks([
  http.Client,
  SharedPreferences,
  GoogleSignIn,
  GoogleSignInAccount,
  GoogleSignInAuthentication,
  WebSocketChannel,
  WebSocketSink,
  WebSocketService,
  AuthService,
  ConversationService,
  ChatService,
  NotificationService,
  SpeechToText,
  ImagePicker,
])
void main() {}
