import 'package:flutter/foundation.dart';

import '../../models/eligibility.dart';

/// Citizen-friendly presentation of a structured eligibility result.
///
/// This layer talks in citizen terms. It never exposes raw engine internals
/// such as `Expected:/Current:`, rule codes used as user-facing text, or
/// source chunks on the normal citizen UI.
@immutable
class EligibilityPresentation {
  const EligibilityPresentation({
    required this.status,
    required this.statusLabel,
    required this.whyYouMatch,
    required this.missingDocuments,
    required this.missingInformation,
    required this.missingProfilePrompts,
    required this.benefitSummary,
    required this.nextAction,
    required this.showDetailedRules,
    this.raw,
  });

  final EligibilityStatus status;
  final String statusLabel;
  final List<String> whyYouMatch;
  final List<String> missingDocuments;
  final List<String> missingInformation;
  final List<String> missingProfilePrompts;
  final String benefitSummary;
  final NextAction nextAction;
  final bool showDetailedRules;
  final EligibilityCheck? raw;

  static const _maxMatchBullets = 3;
  static const _maxMissingBullets = 3;
}

enum EligibilityStatus {
  eligible,
  insufficientInformation,
  notEligible,
  manualReviewRequired,
  unknown,
}

enum NextAction {
  none,
  viewScheme,
  completeProfile,
  uploadDocuments,
  proceedToApplication,
}

extension EligibilityStatusX on EligibilityStatus {
  String get citizenLabel {
    switch (this) {
      case EligibilityStatus.eligible:
        return 'You may be eligible';
      case EligibilityStatus.insufficientInformation:
        return 'More information needed';
      case EligibilityStatus.notEligible:
        return 'You are not currently eligible';
      case EligibilityStatus.manualReviewRequired:
        return 'Manual verification required';
      case EligibilityStatus.unknown:
        return 'We could not verify this yet';
    }
  }
}

/// Converts a raw eligibility check into a citizen-facing presentation.
@immutable
class EligibilityPresentationPresenter {
  const EligibilityPresentationPresenter();

  EligibilityPresentation present(EligibilityCheck check) {
    final matchedRules = check.matchedRules;
    final failedRules = check.failedRules;
    final reasoning = check.reasoning;
    final eligible = check.eligible;
    final applicationReady = check.applicationReady;
    final eligibilityStatus = check.eligibilityStatus;

    // Build match bullets (max 3)
    final whyBullets = <String>[];
    for (final rule in matchedRules) {
      if (whyBullets.length >= EligibilityPresentation._maxMatchBullets) break;
      final sentence = _matchedSentence(rule);
      if (sentence.isNotEmpty) {
        whyBullets.add(sentence);
      }
    }

    // Build missing document bullets (max 3)
    final missingDocs = <String>[];
    for (final rule in failedRules.where((r) => r.looksDocumentRelated)) {
      if (missingDocs.length >= EligibilityPresentation._maxMissingBullets) break;
      final sentence = _missingDocumentSentence(rule);
      if (sentence.isNotEmpty) {
        missingDocs.add(sentence);
      }
    }
    for (final doc in check.requiredDocuments.where((d) => d.trim().isNotEmpty)) {
      if (missingDocs.length >= EligibilityPresentation._maxMissingBullets) break;
      if (missingDocs.any((m) => m.toLowerCase().contains(doc.toLowerCase().trim()))) {
        continue;
      }
      missingDocs.add('You still need to provide ${doc.trim()}.');
    }

    // Build missing profile bullets (max 3)
    final missingInfo = <String>[];
    for (final rule in failedRules.where((r) => r.hasMissingProfileValue)) {
      if (missingInfo.length >= EligibilityPresentation._maxMissingBullets) break;
      final sentence = _missingProfileSentence(rule);
      if (sentence.isNotEmpty) {
        missingInfo.add(sentence);
      }
    }

    // Build missing profile prompts from profile fields
    final missingProfilePrompts = <String>[];
    final missingProfileItems = check.missingProfileInformation;
    for (final item in missingProfileItems.take(EligibilityPresentation._maxMissingBullets)) {
      final label = item.displayTitle.trim();
      if (label.isNotEmpty) {
        missingProfilePrompts.add('Please provide $label.');
      }
    }

    // Choose status
    var status = EligibilityStatus.unknown;
    if (eligible && applicationReady && failedRules.isEmpty && missingProfilePrompts.isEmpty) {
      status = EligibilityStatus.eligible;
    } else if (!applicationReady ||
        failedRules.isNotEmpty ||
        missingProfilePrompts.isNotEmpty) {
      status = EligibilityStatus.insufficientInformation;
    } else {
      status = EligibilityStatus.notEligible;
    }

    final action = _chooseNextAction(
      eligible: eligible,
      applicationReady: applicationReady,
      missingDocuments: missingDocs,
      missingProfilePrompts: missingProfilePrompts,
      missingInformation: missingInfo,
    );
    final showRules = eligibilityStatus != 'manual_review_required' &&
        matchedRules.isNotEmpty &&
        failedRules.isNotEmpty &&
        missingDocs.isEmpty;

    return EligibilityPresentation(
      status: status,
      statusLabel: status.citizenLabel,
      whyYouMatch: whyBullets,
      missingDocuments: missingDocs,
      missingProfilePrompts: missingProfilePrompts,
      missingInformation: missingInfo,
      benefitSummary: _shortBenefitSummary(reasoning),
      nextAction: action,
      showDetailedRules: showRules,
      raw: check,
    );
  }

  NextAction _chooseNextAction({
    required bool eligible,
    required bool applicationReady,
    required List<String> missingDocuments,
    required List<String> missingProfilePrompts,
    required List<String> missingInformation,
  }) {
    if (!applicationReady && missingDocuments.isNotEmpty) {
      return NextAction.uploadDocuments;
    }
    if (missingProfilePrompts.isNotEmpty) {
      return NextAction.completeProfile;
    }
    if (eligible && applicationReady) {
      return NextAction.proceedToApplication;
    }
    if (missingDocuments.isNotEmpty ||
        missingProfilePrompts.isNotEmpty ||
        missingInformation.isNotEmpty) {
      return NextAction.completeProfile;
    }
    return NextAction.viewScheme;
  }

  String _shortBenefitSummary(String reasoning) {
    final base = reasoning.trim();
    if (base.isEmpty) return 'Review the scheme page for benefit details.';
    if (base.length <= 180) return base;
    return '${base.substring(0, 177)}...';
  }

  static String _matchedSentence(EligibilityRuleResult rule) {
    if (rule.displayTitle.trim().isEmpty) return '';
    return "Your information matches this scheme's requirement.";
  }

  static String _missingDocumentSentence(EligibilityRuleResult rule) {
    if (rule.displayTitle.trim().isEmpty) {
      return 'You still need to provide a required document.';
    }
    return 'Please provide the required supporting document.';
  }

  static String _missingProfileSentence(EligibilityRuleResult rule) {
    if (rule.displayTitle.trim().isEmpty) {
      return 'We need some additional information before we can confirm your eligibility.';
    }
    return 'We need some additional information about this requirement before we can confirm your eligibility.';
  }
}