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

  static String money(num? value) {
    if (value == null) {
      return 'Not available';
    }
    return NumberFormat.currency(locale: 'en_IN', symbol: '₹', decimalDigits: 0).format(value);
  }

  static String number(num? value, {int decimalDigits = 2}) {
    if (value == null) {
      return '0';
    }
    final formatter = NumberFormat.decimalPattern('en_IN')
      ..minimumFractionDigits = decimalDigits
      ..maximumFractionDigits = decimalDigits;
    return formatter.format(value);
  }

  static String titleCase(String? value, {String fallback = 'Not available'}) {
    final text = displayValue(value, fallback: fallback).replaceAll('_', ' ');
    return text
        .split(' ')
        .map((part) => part.isEmpty
            ? part
            : '${part[0].toUpperCase()}${part.substring(1).toLowerCase()}')
        .join(' ');
  }
}
