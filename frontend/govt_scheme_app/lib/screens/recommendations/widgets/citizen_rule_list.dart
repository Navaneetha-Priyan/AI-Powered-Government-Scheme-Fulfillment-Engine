import 'package:flutter/material.dart';

@immutable
class CitizenRuleList extends StatelessWidget {
  const CitizenRuleList({
    super.key,
    required this.title,
    required this.passed,
    required this.missingDocuments,
    required this.missingInformation,
    required this.emptyText,
  });

  final String title;
  final List<String> passed;
  final List<String> missingDocuments;
  final List<String> missingInformation;
  final String emptyText;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bullets = <Widget>[];

    if (passed.isNotEmpty) {
      bullets.addAll(
        passed.map(
          (text) => _Bullet(
            icon: Icons.check_circle,
            iconColor: theme.colorScheme.primary,
            text: text,
          ),
        ),
      );
    }
    if (missingDocuments.isNotEmpty) {
      bullets.addAll(
        missingDocuments.map((text) => _Bullet(
          icon: Icons.document_scanner_outlined,
          iconColor: theme.colorScheme.error,
          text: text,
        )),
      );
    }
    if (missingInformation.isNotEmpty) {
      bullets.addAll(
        missingInformation.map((text) => _Bullet(
          icon: Icons.help_outline,
          iconColor: theme.colorScheme.primary,
          text: text,
        )),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          title,
          style: theme.textTheme.titleMedium,
          softWrap: true,
        ),
        const SizedBox(height: 8),
        if (bullets.isEmpty)
          Text(
            emptyText,
            style: theme.textTheme.bodyMedium,
            softWrap: true,
          )
        else
          ...bullets,
      ],
    );
  }
}

@immutable
class _Bullet extends StatelessWidget {
  const _Bullet({
    required this.icon,
    required this.iconColor,
    required this.text,
  });

  final IconData icon;
  final Color iconColor;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: iconColor),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: Theme.of(context).textTheme.bodyMedium,
              softWrap: true,
            ),
          ),
        ],
      ),
    );
  }
}
