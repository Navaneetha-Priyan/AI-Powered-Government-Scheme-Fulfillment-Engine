import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:record/record.dart';

/// Encapsulates all voice recording logic for the app.
///
/// Phase 1 scope:
///  - Requests microphone permission.
///  - Starts and stops microphone recording.
///  - Saves the recording locally to the app documents directory.
///  - Exposes the saved file path.
///
/// This service intentionally does NOT upload audio or perform any
/// speech-to-text conversion.
class VoiceRecorderService extends ChangeNotifier {
  VoiceRecorderService() {
    _recorder = AudioRecorder();
  }

  late final AudioRecorder _recorder;

  /// Whether the microphone is currently recording.
  bool _isRecording = false;
  bool get isRecording => _isRecording;

  /// Path of the most recently saved audio file (null before any save).
  String? _lastSavedPath;
  String? get lastSavedPath => _lastSavedPath;

  /// True while a permission or recording operation is in progress.
  bool _isBusy = false;
  bool get isBusy => _isBusy;

  /// Error message from the last failed operation (null when healthy).
  String? _errorMessage;
  String? get errorMessage => _errorMessage;

  /// Requests microphone permission.
  ///
  /// Returns `true` when permission is granted or already granted.
  Future<bool> requestPermission() async {
    final status = await Permission.microphone.request();
    final granted = status.isGranted;

    _errorMessage = granted
        ? null
        : 'Microphone permission denied. Enable it in app settings.';

    notifyListeners();
    return granted;
  }

  /// Starts recording to a unique local file.
  ///
  /// Throws a [StateError] if already recording.
  Future<void> startRecording() async {
    if (_isRecording) {
      throw StateError('Recording is already in progress.');
    }

    _setBusy(true);
    try {
      final granted = await requestPermission();
      if (!granted) {
        _setBusy(false);
        return;
      }

      final directory = await _recordingDirectory();
      final timestamp = DateTime.now().millisecondsSinceEpoch;
      final path = '${directory.path}${Platform.pathSeparator}rec_$timestamp.m4a';

      final config = const RecordConfig(
        encoder: AudioEncoder.aacLc,
        bitRate: 128000,
        sampleRate: 44100,
        numChannels: 1,
      );

      await _recorder.start(config, path: path);
      _isRecording = true;
      _errorMessage = null;
    } on Exception catch (error) {
      _errorMessage = 'Failed to start recording: $error';
    } finally {
      _setBusy(false);
    }
  }

  /// Stops the active recording and saves the audio file locally.
  ///
  /// Returns the saved file path, or `null` when there was no active
  /// recording or the operation failed.
  Future<String?> stopRecording() async {
    if (!_isRecording) {
      return null;
    }

    _setBusy(true);
    try {
      final path = await _recorder.stop();
      if (path == null || path.isEmpty) {
        _errorMessage = 'Recording stopped but no audio file was produced.';
        return null;
      }

      _lastSavedPath = path;
      _errorMessage = null;
      debugPrint('VoiceRecorderService: Audio saved to $path');
      return path;
    } on Exception catch (error) {
      _errorMessage = 'Failed to save recording: $error';
      return null;
    } finally {
      _isRecording = false;
      _setBusy(false);
    }
  }


/// Deletes a previously saved recording file.
  ///
  /// Used after a successful upload so the local file is cleaned up.
  /// Returns `true` when the file was removed (or did not exist).
  Future<bool> deleteRecording(String path) async {
    try {
      final file = File(path);
      if (!await file.exists()) {
        return true;
      }
      await file.delete();
      if (_lastSavedPath == path) {
        _lastSavedPath = null;
      }
      return true;
    } on Exception catch (error) {
      _errorMessage = 'Failed to delete recording: $error';
      notifyListeners();
      return false;
    }
  }

  /// Resolves the directory used to store recordings, creating it if needed.
  Future<Directory> _recordingDirectory() async {
    final base = await getApplicationDocumentsDirectory();
    final directory = Directory('${base.path}${Platform.pathSeparator}recordings');
    if (!directory.existsSync()) {
      await directory.create(recursive: true);
    }
    return directory;
  }

  void _setBusy(bool busy) {
    _isBusy = busy;
    notifyListeners();
  }

  /// Releases the underlying recorder resources.
  @override
  void dispose() {
    _recorder.dispose();
    super.dispose();
  }
}

