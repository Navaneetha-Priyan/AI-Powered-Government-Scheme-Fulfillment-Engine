import 'package:flutter/material.dart';

class AppTheme {
  static const Color primaryBlue = Color(0xFF0D47A1);
  static const Color secondaryGreen = Color(0xFF1B8A5A);
  static const Color background = Color(0xFFF4F7FB);

  static ThemeData light() {
    final baseScheme =
        ColorScheme.fromSeed(
          seedColor: primaryBlue,
          brightness: Brightness.light,
          surface: Colors.white,
        ).copyWith(
          secondary: secondaryGreen,
          primary: primaryBlue,
          tertiary: const Color(0xFF6A8FD6),
        );

    return _baseTheme(baseScheme, brightness: Brightness.light).copyWith(
      scaffoldBackgroundColor: background,
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: Colors.transparent,
        foregroundColor: primaryBlue,
        titleTextStyle: TextStyle(
          color: primaryBlue,
          fontSize: 24,
          fontWeight: FontWeight.w800,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 1,
        color: Colors.white,
        shadowColor: Colors.black.withValues(alpha: 0.08),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        margin: EdgeInsets.zero,
      ),
    );
  }

  static ThemeData dark() {
    final scheme =
        ColorScheme.fromSeed(
          seedColor: primaryBlue,
          brightness: Brightness.dark,
        ).copyWith(
          primary: const Color(0xFF8CB7FF),
          secondary: const Color(0xFF76D7A7),
          surface: const Color(0xFF121826),
        );

    return _baseTheme(scheme, brightness: Brightness.dark).copyWith(
      scaffoldBackgroundColor: const Color(0xFF0B1020),
      appBarTheme: const AppBarTheme(
        centerTitle: false,
        elevation: 0,
        backgroundColor: Colors.transparent,
        titleTextStyle: TextStyle(fontSize: 24, fontWeight: FontWeight.w800),
      ),
      cardTheme: CardThemeData(
        elevation: 1,
        color: const Color(0xFF121826),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        margin: EdgeInsets.zero,
      ),
    );
  }

  static ThemeData _baseTheme(
    ColorScheme scheme, {
    required Brightness brightness,
  }) {
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      visualDensity: VisualDensity.standard,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: brightness == Brightness.light
            ? Colors.white
            : const Color(0xFF121826),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFE1E7F0)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Color(0xFFE1E7F0)),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: BorderSide(color: scheme.primary, width: 1.8),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(16),
          borderSide: const BorderSide(color: Colors.redAccent),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 18,
          vertical: 18,
        ),
        helperMaxLines: 3,
        errorMaxLines: 2,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: scheme.primary,
          foregroundColor: scheme.onPrimary,
          minimumSize: const Size.fromHeight(58),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(58),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          side: BorderSide(color: scheme.primary.withValues(alpha: 0.45)),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
          ),
          textStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 18),
          foregroundColor: scheme.primary,
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          minimumSize: const Size(56, 48),
          textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: 72,
        labelTextStyle: WidgetStateProperty.resolveWith(
          (_) => const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        ),
        iconTheme: WidgetStateProperty.resolveWith(
          (_) => const IconThemeData(size: 28),
        ),
      ),
      textTheme: const TextTheme(
        headlineLarge: TextStyle(fontWeight: FontWeight.w800, fontSize: 28),
        headlineMedium: TextStyle(fontWeight: FontWeight.w800, fontSize: 24),
        headlineSmall: TextStyle(fontWeight: FontWeight.w800, fontSize: 22),
        titleLarge: TextStyle(fontWeight: FontWeight.w800, fontSize: 22),
        titleMedium: TextStyle(fontWeight: FontWeight.w700, fontSize: 18),
        titleSmall: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
        bodyLarge: TextStyle(height: 1.45, fontSize: 16),
        bodyMedium: TextStyle(height: 1.45, fontSize: 16),
        bodySmall: TextStyle(height: 1.45, fontSize: 14),
        labelLarge: TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
      ),
      snackBarTheme: SnackBarThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        behavior: SnackBarBehavior.floating,
      ),
      dividerTheme: DividerThemeData(color: scheme.outlineVariant),
    );
  }
}
