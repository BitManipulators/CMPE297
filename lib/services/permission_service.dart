import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

class PermissionService extends ChangeNotifier {
  bool _microphonePermission = false;
  bool _cameraPermission = false;
  bool _storagePermission = false;

  bool get microphonePermission => _microphonePermission;
  bool get cameraPermission => _cameraPermission;
  bool get storagePermission => _storagePermission;

  Future<void> requestPermissions() async {
    await Future.wait([
      _requestMicrophonePermission(),
      _requestCameraPermission(),
      _requestStoragePermission(),
    ]);
  }

  Future<void> _requestMicrophonePermission() async {
    final status = await Permission.microphone.request();
    _microphonePermission = status.isGranted;
    notifyListeners();
  }

  Future<void> _requestCameraPermission() async {
    final status = await Permission.camera.request();
    _cameraPermission = status.isGranted;
    notifyListeners();
  }

  Future<void> _requestStoragePermission() async {
    final status = await Permission.photos.request();
    _storagePermission = status.isGranted;
    notifyListeners();
  }

  Future<bool> checkMicrophonePermission() async {
    final status = await Permission.microphone.status;
    _microphonePermission = status.isGranted;
    notifyListeners();
    return _microphonePermission;
  }

  Future<bool> checkCameraPermission() async {
    final status = await Permission.camera.status;
    _cameraPermission = status.isGranted;
    notifyListeners();
    return _cameraPermission;
  }

  Future<bool> checkStoragePermission() async {
    final status = await Permission.photos.status;
    _storagePermission = status.isGranted;
    notifyListeners();
    return _storagePermission;
  }
}

