import 'package:flutter/foundation.dart';

import '../../core/localization/app_strings.dart';
import '../../core/utils/evidence_mapping.dart';
import '../../models/eligibility.dart';

/// Citizen-facing presentation of a structured eligibility result.
///
/// This layer talks in citizen terms. It never exposes raw engine internals
/// such as `Expected:/Current:` lines, rule codes as user-facing text,
/// similarity/confidence percentages, or source chunks on the citizen UI.
///
/// Semantics come from the backend's structured condition results:
/// - PASS  -> a "why you match" bullet,
/// - FAIL  -> a genuine not-met requirement (drives "not currently eligible"),
/// - UNKNOWN -> information the citizen can still provide (drives
///   "More information needed"), never mapped to a failure.
@immutable
class EligibilityPresentation {
  const EligibilityPresentation({
    required this.status,
    required this.statusLabel,
    required this.whyYouMatch,
    required this.missingDocuments,
    required this.missingInformation,
    required this.conditionSummary,
    required this.benefitSummary,
    required this.nextAction,
    required this.showDetailedRules,
    this.raw,
  });

  final EligibilityStatus status;
  final String statusLabel;

  /// Factual "3 of 4 conditions met" count (never a percentage).
  final String? conditionSummary;

  /// Sentences describing what already matches the citizen's profile.
  final List<String> whyYouMatch;

  /// Documents the citizen can still upload (human-readable labels).
  final List<String> missingDocuments;

  /// Profile information needed before eligibility can be confirmed.
  final List<String> missingInformation;
  final String benefitSummary;
  final NextAction nextAction;
  final bool showDetailedRules;
  final EligibilityCheck? raw;
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
        return AppStrings.eligibilityYouMayBeEligible;
      case EligibilityStatus.insufficientInformation:
        return AppStrings.eligibilityMoreInformationNeeded;
      case EligibilityStatus.notEligible:
        return AppStrings.eligibilityNotCurrentlyEligible;
      case EligibilityStatus.manualReviewRequired:
        return AppStrings.eligibilityManualVerificationRequired;
      case EligibilityStatus.unknown:
        return AppStrings.eligibilityInformationNotAvailable;
    }
  }
}

/// Converts a raw eligibility check into a citizen-facing presentation.
@immutable
class EligibilityPresentationPresenter {
  const EligibilityPresentationPresenter();

  EligibilityPresentation present(EligibilityCheck check) {
    // -- 1. Classify conditions by their structured result ----------------
    final passedConditions = <EligibilityRuleResult>[];
    final failedConditions = <EligibilityRuleResult>[];
    final unknownConditions = <EligibilityRuleResult>[];

    void classify(EligibilityRuleResult rule) {
      switch (rule.effectiveResult) {
        case 'PASS':
        case 'NOT_APPLICABLE':
          passedConditions.add(rule);
          break;
        case 'FAIL':
          failedConditions.add(rule);
          break;
        case 'UNKNOWN':
        default:
          unknownConditions.add(rule);
          break;
      }
    }

    check.matchedRules.forEach(classify);
    check.failedRules.forEach(classify);

    // -- 2. Citizen bullets (capped, human-readable, no raw values) -------
    final whyBullets = <String>[];
    for (final rule in passedConditions) {
      if (whyBullets.length >= _maxMatchBullets) break;
      final sentence = _passedSentence(rule);
      if (sentence.isNotEmpty) whyBullets.add(sentence);
    }

    final missingDocs = <String>[];
    final missingInfo = <String>[];
    final hardFails = <EligibilityRuleResult>[];
    for (final rule in failedConditions) {
      if (_isDocumentRequirement(rule)) {
        _addUnique(missingDocs, _missingDocumentSentence(rule));
      } else {
        hardFails.add(rule);
      }
    }
    for (final rule in unknownConditions) {
      if (_isProfileRequirement(rule)) {
        _addUnique(missingInfo, _missingInfoSentence(rule));
      } else if (_isDocumentRequirement(rule) || rule.looksDocumentRelated) {
        _addUnique(missingDocs, _missingDocumentSentence(rule));
      } else {
        _addUnique(missingInfo, _missingInfoSentence(rule));
      }
    }
    if (check.evidenceChecklist.isNotEmpty) {
      // Authoritative evidence wins: report only requirements the backend
      // still marks as needed. A verified/held document can never be
      // listed as missing, so this never contradicts the backend's
      // "Documents & evidence" states. Rule-derived bullets above already
      // covered the engine's own document conditions; this pass adds
      // requirements only the checklist exposes (e.g. bank_account).
      for (final entry in check.evidenceChecklist) {
        if (entry.status.isHeld ||
            entry.status == EvidenceStatus.manual) {
          continue;
        }
        if (entry.kind == EvidenceKind.profileInfo) {
          _addUnique(
              missingInfo,
              entry.profilePrompt ??
                  'We need to know ${entry.label} before we can confirm '
                  'your eligibility.');
          continue;
        }
        _addUnique(
            missingDocs, 'You still need to provide ${entry.label}.');
      }
    } else {
      // Legacy payloads carry no checklist: fall back to the engine's
      // required-document list, as before.
      for (final doc in check.requiredDocuments) {
        if (missingDocs.length >= _maxMissingBullets) break;
        final label = humanizeEvidenceRequirement(doc.trim().toLowerCase());
        _addUnique(missingDocs, 'You still need to provide $label.');
      }
    }

    // -- 3. Status: the backend decision wins; frontend only refines ------
    final status = _resolveStatus(check, hardFails, missingDocs, missingInfo);

    // -- 4. Factual condition count (never a percentage) -------------------
    final conditionSummary = check.conditionSummary;

    final action = _chooseNextAction(
      status: status,
      applicationReady: check.applicationReady,
      missingDocuments: missingDocs,
      missingInformation: missingInfo,
    );

    return EligibilityPresentation(
      status: status,
      statusLabel: status.citizenLabel,
      conditionSummary: conditionSummary,
      whyYouMatch: whyBullets,
      missingDocuments: missingDocs,
      missingInformation: missingInfo,
      benefitSummary: '',
      nextAction: action,
      showDetailedRules:
          check.matchedRules.isNotEmpty || check.failedRules.isNotEmpty,
      raw: check,
    );
  }

  /// Citizen status mapping shared with the recommendation screens.
  /// The backend's deterministic decision is preserved — unknown statuses
  /// fall back conservatively to "more information needed" instead of
  /// wrongly rejecting the citizen.
  static EligibilityStatus statusFromBackend(String rawStatus) {
    final s = rawStatus.trim().toLowerCase().replaceAll(' ', '_');
    switch (s) {
      case 'eligible':
        return EligibilityStatus.eligible;
      case 'potentially_eligible':
      case 'possibly_eligible':
      case 'insufficient_information':
      case 'more_information_needed':
        return EligibilityStatus.insufficientInformation;
      case 'not_eligible':
      case 'ineligible':
        return EligibilityStatus.notEligible;
      case 'manual_review_required':
        return EligibilityStatus.manualReviewRequired;
      default:
        return EligibilityStatus.unknown;
    }
  }

  /// Citizen label for a raw backend status string; empty/unknown values
  /// fall back to a neutral prompt instead of leaking internal names.
  static String citizenStatusLabel(String rawStatus) {
    final trimmed = rawStatus.trim();
    if (trimmed.isEmpty || trimmed.toLowerCase() == 'unknown') {
      return AppStrings.eligibilityInformationNotAvailable;
    }
    return statusFromBackend(trimmed).citizenLabel;
  }

  EligibilityStatus _resolveStatus(
    EligibilityCheck check,
    List<EligibilityRuleResult> hardFails,
    List<String> missingDocs,
    List<String> missingInfo,
  ) {
    final status = statusFromBackend(check.eligibilityStatus);
    if (status == EligibilityStatus.unknown) {
      // No recognizable backend status: derive from conditions.
      if (hardFails.isNotEmpty) {
        return EligibilityStatus.notEligible;
      }
      if (missingDocs.isNotEmpty || missingInfo.isNotEmpty) {
        return EligibilityStatus.insufficientInformation;
      }
      if (check.eligible && check.applicationReady) {
        return EligibilityStatus.eligible;
      }
      return EligibilityStatus.unknown;
    }
    // Sanity refinement: an "eligible" decision with genuinely failed
    // mandatory conditions is downgraded, never upgraded.
    if (status == EligibilityStatus.eligible && hardFails.isNotEmpty) {
      return EligibilityStatus.notEligible;
    }
    return status;
  }

  NextAction _chooseNextAction({
    required EligibilityStatus status,
    required bool applicationReady,
    required List<String> missingDocuments,
    required List<String> missingInformation,
  }) {
    switch (status) {
      case EligibilityStatus.notEligible:
      case EligibilityStatus.manualReviewRequired:
      case EligibilityStatus.unknown:
        return NextAction.viewScheme;
      case EligibilityStatus.eligible:
      case EligibilityStatus.insufficientInformation:
        break;
    }
    if (!applicationReady && missingDocuments.isNotEmpty) {
      return NextAction.uploadDocuments;
    }
    if (missingInformation.isNotEmpty) {
      return NextAction.completeProfile;
    }
    if (status == EligibilityStatus.eligible && applicationReady) {
      return NextAction.proceedToApplication;
    }
    return NextAction.viewScheme;
  }

  // -- Citizen sentence helpers -------------------------------------------

  static const _maxMatchBullets = 3;
  static const _maxMissingBullets = 3;

  static void _addUnique(List<String> target, String sentence) {
    if (sentence.isEmpty || target.length >= _maxMissingBullets) return;
    if (!target.contains(sentence)) target.add(sentence);
  }

  String _passedSentence(EligibilityRuleResult rule) {
    final note = _citizenNote(rule);
    if (note != null) return note;
    final label = _conditionLabel(rule);
    if (label.isEmpty) return '';
    return "Your $label matches this scheme's requirement.";
  }

  String _missingDocumentSentence(EligibilityRuleResult rule) {
    final note = _citizenNote(rule);
    if (note != null && note.toLowerCase().contains('need')) return note;
    final label = _documentLabel(rule);
    if (label.isEmpty) return '';
    return 'You still need to provide $label.';
  }

  String _missingInfoSentence(EligibilityRuleResult rule) {
    final note = _citizenNote(rule);
    if (note != null) return note;
    final label = _conditionLabel(rule);
    if (label.isEmpty) return '';
    return 'We need to know $label before we can confirm your eligibility.';
  }

  /// Curated note from the catalogue evaluator, when it is citizen-safe.
  String? _citizenNote(EligibilityRuleResult rule) {
    final note = (rule.notes ?? '').trim();
    if (note.isEmpty || note.length > 140) return null;
    if (note.contains('_')) return null;
    if (note.toLowerCase().contains('manual_review')) return null;
    return note[0].toUpperCase() + note.substring(1);
  }

  String _conditionLabel(EligibilityRuleResult rule) {
    final mapped = humanizeEvidenceRequirement(rule.evidenceKey);
    if (!mapped.toLowerCase().contains('requirement')) return mapped;
    final label = (rule.description ?? rule.condition).trim();
    return label.replaceAll('_', ' ');
  }

  String _documentLabel(EligibilityRuleResult rule) {
    final mapping = evidenceMappingFor(rule.evidenceKey);
    if (mapping != null) return mapping.label;
    return _conditionLabel(rule);
  }

  /// Document requirements route to the upload bucket.
  bool _isDocumentRequirement(EligibilityRuleResult rule) =>
      evidenceMappingFor(rule.evidenceKey)?.kind == EvidenceKind.document;

  /// Profile-information requirements route to the "we need to know" bucket.
  bool _isProfileRequirement(EligibilityRuleResult rule) =>
      evidenceMappingFor(rule.evidenceKey)?.kind == EvidenceKind.profileInfo;
}
