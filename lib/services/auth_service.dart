import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import '../models/user.dart';
import '../config/app_config.dart';

class AuthService extends ChangeNotifier {
  static String get _baseUrl => AppConfig.backendBaseUrl;
  User? _currentUser;
  bool _isAuthenticated = false;

  User? get currentUser => _currentUser;
  bool get isAuthenticated => _isAuthenticated;

  AuthService() {
    _loadUser();
  }

  Future<void> _loadUser() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final userJson = prefs.getString('current_user');
      if (userJson != null) {
        _currentUser = User.fromJson(json.decode(userJson));
        _isAuthenticated = true;
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Error loading user: $e');
    }
  }

  Future<User> register(String username, {String? email}) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/users/register'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'username': username,
          'email': email,
        }),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw Exception(
            'Connection timeout. Please check if the backend server is running at $_baseUrl',
          );
        },
      );

      if (response.statusCode == 200) {
        final userData = json.decode(response.body);
        _currentUser = User.fromJson(userData);
        _isAuthenticated = true;

        // Save to local storage
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('current_user', json.encode(userData));

        notifyListeners();
        return _currentUser!;
      } else {
        throw Exception('Failed to register user: ${response.body}');
      }
    } on http.ClientException catch (e) {
      throw Exception(
        'Cannot connect to backend server at $_baseUrl. '
        'Please ensure the server is running. '
        'Error: ${e.message}',
      );
    } catch (e) {
      // Check if it's a connection error
      final errorString = e.toString().toLowerCase();
      if (errorString.contains('failed to fetch') ||
          errorString.contains('connection refused') ||
          errorString.contains('network is unreachable')) {
        throw Exception(
          'Cannot connect to backend server at $_baseUrl. '
          'Please ensure the server is running. '
        );
      }
      rethrow;
    }
  }

  Future<User?> getUser(String userId) async {
    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/users/$userId'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return User.fromJson(json.decode(response.body));
      }
      return null;
    } catch (e) {
      debugPrint('Error getting user: $e');
      return null;
    }
  }

  Future<User> signInWithGoogle() async {
    try {
      // For web, we need to pass the clientId
      final clientId = kIsWeb ? AppConfig.googleClientId : null;

      final GoogleSignIn googleSignIn = GoogleSignIn(
        scopes: ['email', 'profile', 'openid'],
        clientId: clientId,
      );

      final GoogleSignInAccount? googleUser = await googleSignIn.signIn();
      if (googleUser == null) {
        throw Exception('Google sign-in was cancelled');
      }

      final GoogleSignInAuthentication googleAuth = await googleUser.authentication;

      // Use access token as fallback if idToken is not available (common on web)
      if (googleAuth.idToken == null && googleAuth.accessToken == null) {
        throw Exception(
          'Both ID token and access token are missing. This may be a configuration issue. '
          'Ensure your Google OAuth Client ID is properly configured and includes "openid" scope.'
        );
      }

      // Send tokens to backend for verification
      // Backend will use idToken if available, otherwise fallback to accessToken
      final requestBody = <String, dynamic>{};
      if (googleAuth.idToken != null && googleAuth.idToken!.isNotEmpty) {
        requestBody['idToken'] = googleAuth.idToken;
      }
      if (googleAuth.accessToken != null && googleAuth.accessToken!.isNotEmpty) {
        requestBody['accessToken'] = googleAuth.accessToken;
      }

      // Ensure we have at least one token
      if (requestBody.isEmpty) {
        throw Exception(
          'No valid tokens received from Google. ID token and access token are both missing or empty.'
        );
      }

      final response = await http.post(
        Uri.parse('$_baseUrl/api/auth/google'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode(requestBody),
      ).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw Exception(
            'Connection timeout. Please check if the backend server is running at $_baseUrl',
          );
        },
      );

      if (response.statusCode == 200) {
        final userData = json.decode(response.body);
        _currentUser = User.fromJson(userData);
        _isAuthenticated = true;

        // Save to local storage
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('current_user', json.encode(userData));

        notifyListeners();
        return _currentUser!;
      } else {
        throw Exception('Failed to sign in with Google: ${response.body}');
      }
    } on http.ClientException catch (e) {
      throw Exception(
        'Cannot connect to backend server at $_baseUrl. '
        'Please ensure the server is running. '
        'Error: ${e.message}',
      );
    } catch (e) {
      // Check if it's a connection error
      final errorString = e.toString().toLowerCase();
      if (errorString.contains('failed to fetch') ||
          errorString.contains('connection refused') ||
          errorString.contains('network is unreachable')) {
        throw Exception(
          'Cannot connect to backend server at $_baseUrl. '
          'Please ensure the server is running. '
        );
      }
      rethrow;
    }
  }

  Future<void> logout() async {
    // Sign out from Google if signed in
    try {
      final GoogleSignIn googleSignIn = GoogleSignIn(
        clientId: kIsWeb && AppConfig.googleClientId != null
            ? AppConfig.googleClientId
            : null,
      );
      await googleSignIn.signOut();
    } catch (e) {
      debugPrint('Error signing out from Google: $e');
    }

    _currentUser = null;
    _isAuthenticated = false;

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('current_user');

    notifyListeners();
  }
}

