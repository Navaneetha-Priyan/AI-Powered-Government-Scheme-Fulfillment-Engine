import 'package:intl/intl.dart';

class AppFormatters {
  AppFormatters._();

  static final DateFormat dateTimeFormat = DateFormat('dd MMM yyyy, hh:mm a');
  static final DateFormat dateFormat = DateFormat('dd MMM yyyy');

  static String displayDateTime(DateTime? value) {
    if (value == null) {
      return 'Not available';
    }
    return dateTimeFormat.format(value.toLocal());
  }

  static String displayDate(DateTime? value) {
    if (value == null) {
      return 'Not available';
    }
    return dateFormat.format(value.toLocal());
  }

  static String displayValue(String? value, {String fallback = 'Not available'}) {
    if (value == null || value.trim().isEmpty) {
      return fallback;
    }
    return value;
  }
}
