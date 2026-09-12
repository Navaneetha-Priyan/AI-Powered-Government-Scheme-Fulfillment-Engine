import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/network/api_exception.dart';
import '../../core/services/voice_api_service.dart';
import '../../core/services/voice_recorder_service.dart';

enum VoicePipelineStage {
  idle,
  recording,
  uploading,
  transcribing,
  normalizing,
  retrieving,
  completed,
  error,
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<_ChatMessage> _messages = [];

  VoicePipelineStage _stage = VoicePipelineStage.idle;
  String? _errorMessage;

  bool get _isProcessing =>
      _stage == VoicePipelineStage.uploading ||
      _stage == VoicePipelineStage.transcribing ||
      _stage == VoicePipelineStage.normalizing ||
      _stage == VoicePipelineStage.retrieving;

  @override
  Widget build(BuildContext context) {
    return Consumer<VoiceRecorderService>(
      builder: (context, voiceService, _) {
        final currentStage = voiceService.isRecording
            ? VoicePipelineStage.recording
            : _stage;

        return Scaffold(
          appBar: AppBar(title: const Text('Voice Assistant')),
          body: Column(
            children: [
              _StatusBanner(stage: currentStage, errorMessage: _errorMessage),
              Expanded(
                child:
                    _messages.isEmpty && currentStage == VoicePipelineStage.idle
                    ? const _EmptyState()
                    : _ChatMessageList(messages: _messages),
              ),
            ],
          ),
          floatingActionButton: _MicrophoneButton(
            stage: currentStage,
            isDisabled: _isProcessing || voiceService.isBusy,
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
    if (_isProcessing || voiceService.isBusy) {
      return;
    }

    if (voiceService.isRecording) {
      final path = await voiceService.stopRecording();
      debugPrint('[VOICE] Recording stopped');
      if (!context.mounted) {
        return;
      }

      if (path == null) {
        _setError('Could not record audio. Please try again.');
        return;
      }

      await _runVoicePipeline(context, voiceService, path);
      return;
    }

    await voiceService.startRecording();
    if (!context.mounted) {
      return;
    }

    if (voiceService.isRecording) {
      debugPrint('[VOICE] Recording started');
      setState(() {
        _stage = VoicePipelineStage.recording;
        _errorMessage = null;
      });
    } else {
      _setError('Could not record audio. Please try again.');
    }
  }

  Future<void> _runVoicePipeline(
    BuildContext context,
    VoiceRecorderService voiceService,
    String path,
  ) async {
    final voiceApiService = context.read<VoiceApiService>();

    _appendMessage(
      const _ChatMessage(
        role: _ChatRole.user,
        title: 'Voice message',
        text: 'Audio recorded',
      ),
    );

    try {
      _setStage(VoicePipelineStage.uploading);
      await Future<void>.delayed(Duration.zero);
      _setStage(VoicePipelineStage.transcribing);
      final transcription = await voiceApiService.transcribe(path);
      await voiceService.deleteRecording(path);

      final transcript = transcription.text.trim();
      if (transcript.isEmpty) {
        _setError(
          "I couldn't understand the voice recording. Please try again.",
        );
        return;
      }

      _appendMessage(
        _ChatMessage(
          role: _ChatRole.system,
          title: 'Transcription',
          text: transcript,
        ),
      );

      _setStage(VoicePipelineStage.normalizing);
      final normalization = await voiceApiService.normalize(transcript);
      final normalizedText = normalization.normalizedText.trim();
      if (normalizedText.isEmpty) {
        _setError("I couldn't understand your request. Please try again.");
        return;
      }

      _appendMessage(
        _ChatMessage(
          role: _ChatRole.system,
          title: 'Understanding',
          text: normalizedText,
        ),
      );

      _setStage(VoicePipelineStage.retrieving);
      final recommendation = await voiceApiService.recommend(
        transcript,
        normalization: normalization,
      );
      final responseText = recommendation.responseText?.trim();
      final displayText = responseText == null || responseText.isEmpty
          ? recommendation.message?.trim().isNotEmpty == true
                ? recommendation.message!.trim()
                : 'I could not generate a response for this request.'
          : responseText;

      _appendMessage(
        _ChatMessage(
          role: _ChatRole.assistant,
          title: 'Government scheme answer',
          text: displayText,
        ),
      );
      _setStage(VoicePipelineStage.completed);
    } on ApiException catch (error) {
      _setError(_friendlyApiMessage(error));
    } on Exception {
      _setError('Unable to connect to the server.');
    }
  }

  String _friendlyApiMessage(ApiException error) {
    if (error.statusCode == 401) {
      return 'Please sign in again to use the voice assistant.';
    }

    switch (_stage) {
      case VoicePipelineStage.transcribing:
      case VoicePipelineStage.uploading:
        return "I couldn't understand the voice recording. Please try again.";
      case VoicePipelineStage.normalizing:
        return "I couldn't understand your request. Please try again.";
      case VoicePipelineStage.retrieving:
        return "I couldn't find relevant government scheme information.";
      case VoicePipelineStage.idle:
      case VoicePipelineStage.recording:
      case VoicePipelineStage.completed:
      case VoicePipelineStage.error:
        return 'Unable to connect to the server.';
    }
  }

  void _setStage(VoicePipelineStage stage) {
    if (!mounted) {
      return;
    }
    setState(() {
      _stage = stage;
      _errorMessage = null;
    });
  }

  void _setError(String message) {
    if (!mounted) {
      return;
    }
    setState(() {
      _stage = VoicePipelineStage.error;
      _errorMessage = message;
    });
  }

  void _appendMessage(_ChatMessage message) {
    if (!mounted) {
      return;
    }
    setState(() {
      _messages.add(message);
      _errorMessage = null;
    });
  }
}

class _StatusBanner extends StatelessWidget {
  const _StatusBanner({required this.stage, required this.errorMessage});

  final VoicePipelineStage stage;
  final String? errorMessage;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isError = stage == VoicePipelineStage.error;
    final statusText = isError
        ? errorMessage ?? 'Something went wrong. Please try again.'
        : _stageLabel(stage);

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      color: isError
          ? theme.colorScheme.errorContainer
          : theme.colorScheme.surfaceContainerHighest,
      child: Row(
        children: [
          if (_stageShowsProgress(stage))
            const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else
            Icon(
              isError
                  ? Icons.error_outline_rounded
                  : Icons.info_outline_rounded,
              size: 20,
            ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              statusText,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: isError
                    ? theme.colorScheme.onErrorContainer
                    : theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }

  bool _stageShowsProgress(VoicePipelineStage stage) {
    return stage == VoicePipelineStage.uploading ||
        stage == VoicePipelineStage.transcribing ||
        stage == VoicePipelineStage.normalizing ||
        stage == VoicePipelineStage.retrieving;
  }

  String _stageLabel(VoicePipelineStage stage) {
    switch (stage) {
      case VoicePipelineStage.idle:
        return 'Tap to speak';
      case VoicePipelineStage.recording:
        return 'Listening... tap again to stop';
      case VoicePipelineStage.uploading:
        return 'Processing your voice...';
      case VoicePipelineStage.transcribing:
        return 'Transcribing...';
      case VoicePipelineStage.normalizing:
        return 'Understanding your request...';
      case VoicePipelineStage.retrieving:
        return 'Finding government schemes...';
      case VoicePipelineStage.completed:
        return 'Done';
      case VoicePipelineStage.error:
        return 'Something went wrong. Please try again.';
    }
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.mic_none_rounded,
              size: 76,
              color: theme.colorScheme.primary,
            ),
            const SizedBox(height: 20),
            Text(
              'Tap the microphone and ask about a government scheme',
              textAlign: TextAlign.center,
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 10),
            Text(
              'Tamil, English, and Tanglish are supported.',
              textAlign: TextAlign.center,
              style: theme.textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}

class _ChatMessageList extends StatelessWidget {
  const _ChatMessageList({required this.messages});

  final List<_ChatMessage> messages;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: messages.length,
      itemBuilder: (context, index) => _MessageBubble(message: messages[index]),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message});

  final _ChatMessage message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isUser = message.role == _ChatRole.user;
    final isAssistant = message.role == _ChatRole.assistant;
    final background = isUser
        ? theme.colorScheme.primaryContainer
        : isAssistant
        ? theme.colorScheme.secondaryContainer
        : theme.colorScheme.surfaceContainerHighest;
    final foreground = isUser
        ? theme.colorScheme.onPrimaryContainer
        : isAssistant
        ? theme.colorScheme.onSecondaryContainer
        : theme.colorScheme.onSurfaceVariant;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        constraints: const BoxConstraints(maxWidth: 420),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: isUser
              ? CrossAxisAlignment.end
              : CrossAxisAlignment.start,
          children: [
            Text(
              message.title,
              style: theme.textTheme.labelMedium?.copyWith(
                color: foreground,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              message.text,
              style: theme.textTheme.bodyMedium?.copyWith(color: foreground),
            ),
          ],
        ),
      ),
    );
  }
}

class _MicrophoneButton extends StatelessWidget {
  const _MicrophoneButton({
    required this.stage,
    required this.isDisabled,
    required this.onPressed,
  });

  final VoicePipelineStage stage;
  final bool isDisabled;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    final isRecording = stage == VoicePipelineStage.recording;
    final theme = Theme.of(context);
    return FloatingActionButton.large(
      onPressed: isDisabled ? null : onPressed,
      backgroundColor: isRecording
          ? theme.colorScheme.error
          : theme.colorScheme.primary,
      foregroundColor: isRecording
          ? theme.colorScheme.onError
          : theme.colorScheme.onPrimary,
      tooltip: isRecording ? 'Stop recording' : 'Start recording',
      child: Icon(
        isRecording ? Icons.stop_rounded : Icons.mic_rounded,
        size: 36,
      ),
    );
  }
}

enum _ChatRole { user, system, assistant }

@immutable
class _ChatMessage {
  const _ChatMessage({
    required this.role,
    required this.title,
    required this.text,
  });

  final _ChatRole role;
  final String title;
  final String text;
}
