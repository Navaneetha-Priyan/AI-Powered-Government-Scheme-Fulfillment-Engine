/// Represents the response from the backend speech-to-text endpoint.
///
/// The `POST /voice/transcribe` endpoint returns a JSON body of the shape
/// `{"text": "<transcribed speech>"}`.
class TranscriptionResult {
  const TranscriptionResult({required this.text});

  /// The transcribed speech returned by the backend.
  final String text;

  /// Builds a [TranscriptionResult] from a decoded JSON [map].
  factory TranscriptionResult.fromJson(Map<String, dynamic> map) {
    return TranscriptionResult(
      text: map['text']?.toString() ?? '',
    );
  }
}
