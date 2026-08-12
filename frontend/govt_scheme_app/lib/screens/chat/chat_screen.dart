import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/services/voice_api_service.dart';
import '../../core/services/voice_recorder_service.dart';
import '../../models/voice_recommendation.dart';

/// Chat screen with a microphone button for recording and transcribing voice.
///
/// Phase 3 scope: after the user stops recording, the audio file is uploaded
/// to the backend `/voice/transcribe` endpoint through [VoiceApiService].
/// While uploading a loading indicator is shown. On success the transcript is
/// displayed as a user chat message and the temporary audio file is deleted.
/// On failure the file is kept and an error Snackbar is shown.
///
/// Phase 5 scope: after a successful transcription, the transcript is sent to
/// the backend `POST /voice/recommend` endpoint. The returned personalized
/// scheme recommendations are displayed as assistant chat messages using the
/// existing recommendation data model.
class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  /// Transcripts returned by the backend, displayed as user chat messages.
  final List<String> _transcripts = [];

  /// Recommendation results (or structured messages) returned for each query.
  final List<VoiceRecommendationResult> _recommendations = [];

  /// True while an audio file is being uploaded/transcribed.
  bool _isUploading = false;

  @override
  Widget build(BuildContext context) {
    return Consumer<VoiceRecorderService>(
      builder: (context, voiceService, _) {
        return Scaffold(
          appBar: AppBar(
            title: const Text('Voice Assistant'),
            actions: [
              if (voiceService.lastSavedPath != null)
                IconButton(
                  tooltip: 'Recording saved',
                  onPressed: () => _showSavedPath(context, voiceService),
                  icon: const Icon(Icons.info_outline_rounded),
                ),
            ],
          ),
          body: _ChatBody(
            voiceService: voiceService,
            transcripts: _transcripts,
            recommendations: _recommendations,
            isUploading: _isUploading,
          ),
          floatingActionButton: _MicrophoneButton(
            isRecording: voiceService.isRecording,
            isUploading: _isUploading,
            onPressed: () => _onMicPressed(context, voiceService),
          ),
        );
      },
    );
  }

  Future<void> _onMicPressed(
    BuildContext context,
    VoiceRecorderService voiceService,
  ) async {
    if (_isUploading) {
      return;
    }

    if (voiceService.isRecording) {
      // Stop recording and save the file locally.
      final path = await voiceService.stopRecording();
      if (!context.mounted) {
        return;
      }

      if (path == null) {
        _showSnackBar(
          context,
          voiceService.errorMessage ?? 'Recording failed. Please try again.',
        );
        return;
      }

      // Upload the audio, transcribe it, then recommend schemes.
      await _uploadTranscribeAndRecommend(context, voiceService, path);
      return;
    }

    // Start recording (permission is requested inside the service).
    await voiceService.startRecording();
    if (!context.mounted) {
      return;
    }

    if (!voiceService.isRecording && voiceService.errorMessage != null) {
      _showSnackBar(context, voiceService.errorMessage!);
    }
  }

  /// Uploads [path], shows the transcript, then requests recommendations.
  ///
  /// On success the temporary audio file is deleted. On failure the file is
  /// kept so the user can retry, and an error Snackbar is shown.
  Future<void> _uploadTranscribeAndRecommend(
    BuildContext context,
    VoiceRecorderService voiceService,
    String path,
  ) async {
    setState(() => _isUploading = true);
    try {
      final voiceApiService = context.read<VoiceApiService>();

      // 1) Transcribe the audio.
      final result = await voiceApiService.transcribe(path);

      // 2) Delete the local audio file only after a successful upload.
      await voiceService.deleteRecording(path);

      if (!context.mounted) {
        return;
      }

      // 3) Request personalized scheme recommendations for the transcript.
      if (result.text.trim().isNotEmpty) {
        final recommendation = await voiceApiService.recommend(result.text);
        if (!context.mounted) {
          return;
        }
        setState(() {
          _isUploading = false;
          _transcripts.add(result.text);
          _recommendations.add(recommendation);
        });
      } else {
        setState(() {
          _isUploading = false;
          _transcripts.add(result.text);
        });
      }
    } on Exception catch (error) {
      if (!context.mounted) {
        return;
      }
      // Keep the local file on failure so the user can retry.
      setState(() => _isUploading = false);
      _showSnackBar(
        context,
        'Transcription/recommendation failed. Your recording was kept: $error',
      );
    }
  }

  void _showSnackBar(BuildContext context, String message) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  void _showSavedPath(BuildContext context, VoiceRecorderService voiceService) {
    final path = voiceService.lastSavedPath ?? '';
    _showSnackBar(context, 'Saved audio: $path');
  }
}

class _ChatBody extends StatelessWidget {
  const _ChatBody({
    required this.voiceService,
    required this.transcripts,
    required this.recommendations,
    required this.isUploading,
  });

  final VoiceRecorderService voiceService;
  final List<String> transcripts;
  final List<VoiceRecommendationResult> recommendations;
  final bool isUploading;

  @override
  Widget build(BuildContext context) {
    if (transcripts.isEmpty && !voiceService.isRecording) {
      return _EmptyState(
        isRecording: voiceService.isRecording,
        isBusy: voiceService.isBusy,
      );
    }

    return _TranscriptList(
      transcripts: transcripts,
      recommendations: recommendations,
      isRecording: voiceService.isRecording,
      isUploading: isUploading,
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.isRecording, required this.isBusy});

  final bool isRecording;
  final bool isBusy;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              isRecording ? Icons.mic_rounded : Icons.mic_none_rounded,
              size: 72,
              color: isRecording
                  ? theme.colorScheme.error
                  : theme.colorScheme.primary,
            ),
            const SizedBox(height: 20),
            Text(
              isRecording
                  ? 'Recording... tap the microphone to stop'
                  : 'Tap the microphone to start recording',
              textAlign: TextAlign.center,
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Text(
              isBusy
                  ? 'Please wait...'
                  : 'Your recording will be transcribed and schemes recommended.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyLarge,
            ),
          ],
        ),
      ),
    );
  }
}

class _TranscriptList extends StatelessWidget {
  const _TranscriptList({
    required this.transcripts,
    required this.recommendations,
    required this.isRecording,
    required this.isUploading,
  });

  final List<String> transcripts;
  final List<VoiceRecommendationResult> recommendations;
  final bool isRecording;
  final bool isUploading;

  @override
  Widget build(BuildContext context) {
    final itemCount =
        transcripts.length + recommendations.length + (isUploading ? 1 : 0);

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: itemCount,
      itemBuilder: (context, index) {
        if (isUploading &&
            index >= transcripts.length + recommendations.length) {
          return const _UploadingIndicator();
        }
        // Interleave transcripts and recommendations.
        if (index.isOdd && (index - 1) ~/ 2 < recommendations.length) {
          final recIndex = (index - 1) ~/ 2;
          return _RecommendationBubble(result: recommendations[recIndex]);
        }
        final transcriptIndex = index ~/ 2;
        if (transcriptIndex < transcripts.length) {
          return _TranscriptBubble(text: transcripts[transcriptIndex]);
        }
        return const SizedBox.shrink();
      },
    );
  }
}

class _UploadingIndicator extends StatelessWidget {
  const _UploadingIndicator();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          SizedBox(width: 12),
          Text('Processing your voice...'),
        ],
      ),
    );
  }
}

class _TranscriptBubble extends StatelessWidget {
  const _TranscriptBubble({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        constraints: const BoxConstraints(maxWidth: 320),
        decoration: BoxDecoration(
          color: theme.colorScheme.primaryContainer,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              'You said:',
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.onPrimaryContainer,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              text,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onPrimaryContainer,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _RecommendationBubble extends StatelessWidget {
  const _RecommendationBubble({required this.result});

  final VoiceRecommendationResult result;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    String heading;
    if (result.hasSchemes) {
      heading = result.schemes.length == 1
          ? '1 scheme you may qualify for:'
          : '${result.schemes.length} schemes you may qualify for:';
    } else if (result.message != null && result.message!.isNotEmpty) {
      heading = result.message!;
    } else {
      heading = 'I understand you asked about "${result.intent}".';
    }

    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(16),
        constraints: const BoxConstraints(maxWidth: 420),
        decoration: BoxDecoration(
          color: theme.colorScheme.secondaryContainer,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              heading,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSecondaryContainer,
                fontWeight: FontWeight.w600,
              ),
            ),
            if (result.hasSchemes) const SizedBox(height: 8),
            if (result.hasSchemes)
              ...result.schemes.map(
                (match) => Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${match.rankingPosition}. ${match.schemeName}',
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSecondaryContainer,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      if (match.estimatedBenefit != null &&
                          match.estimatedBenefit!.isNotEmpty)
                        Text(
                          'Benefit: ${match.estimatedBenefit}',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSecondaryContainer,
                          ),
                        ),
                      if (match.recommendationReason != null &&
                          match.recommendationReason!.isNotEmpty)
                        Text(
                          match.recommendationReason!,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSecondaryContainer,
                          ),
                        ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _MicrophoneButton extends StatelessWidget {
  const _MicrophoneButton({
    required this.isRecording,
    required this.isUploading,
    required this.onPressed,
  });

  final bool isRecording;
  final bool isUploading;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return FloatingActionButton.large(
      onPressed: isUploading ? null : onPressed,
      backgroundColor: isRecording
          ? Theme.of(context).colorScheme.error
          : Theme.of(context).colorScheme.primary,
      foregroundColor: Theme.of(context).colorScheme.onPrimary,
      child: Icon(
        isRecording ? Icons.stop_rounded : Icons.mic_rounded,
        size: 36,
      ),
    );
  }
}
