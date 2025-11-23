/// Application configuration
/// Update these values to match your backend server
class AppConfig {
  // Backend server URL
  // For Chrome/web browser, use: http://localhost:8001 (or your backend port)
  // For Android emulator, use: http://10.0.2.2:8001
  // For iOS simulator, use: http://localhost:8001
  // For physical device, use your computer's IP: http://192.168.x.x:8001
  static const String backendBaseUrl = String.fromEnvironment(
    'BACKEND_BASE_URL',
    defaultValue: 'http://localhost:8001',
  );
  static const String websocketBaseUrl = String.fromEnvironment(
    'WEBSOCKET_BASE_URL',
    defaultValue: 'ws://localhost:8001',
  );

  // Update these for production
  // static const String backendBaseUrl = 'https://your-backend.com';
  // static const String websocketBaseUrl = 'wss://your-backend.com';
}

