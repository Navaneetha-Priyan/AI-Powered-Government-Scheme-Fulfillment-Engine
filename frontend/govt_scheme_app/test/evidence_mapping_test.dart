import 'package:flutter_test/flutter_test.dart';
import 'package:govt_scheme_app/core/utils/evidence_mapping.dart';

void main() {
  test('task examples map to explicit upload slots', () {
    expect(
      evidenceMappingFor('identity_proof')!.documentTypes,
      ['aadhaar_card'],
    );
    expect(
      evidenceMappingFor('address_proof')!.documentTypes,
      contains('smart_ration_card'),
    );
    expect(
      evidenceMappingFor('farmer_registration')!.documentTypes,
      ['farmer_document'],
    );
    expect(
      evidenceMappingFor('land_ownership_proof')!.documentTypes,
      ['land_document'],
    );
    expect(
      evidenceMappingFor('community_certificate')!.documentTypes,
      ['community_certificate'],
    );
    expect(
      evidenceMappingFor('income_proof')!.documentTypes,
      ['income_certificate'],
    );
    // Every mapped upload slot is something the app can actually collect.
    for (final entry in kDocumentEvidenceMappings.values) {
      expect(
        entry.documentTypes.every(
          (doc) => kSupportedUploadDocumentTypes.contains(doc),
        ),
        isTrue,
        reason: '${entry.requirement} maps to unsupported upload type',
      );
    }
  });

  test('satisfaction requires an explicit accepted upload', () {
    final items = resolveEvidenceChecklist(
      ['identity_proof'],
      {'bank_passbook'}.toSet(),
    );
    expect(items.single.status, EvidenceStatus.needed);

    final satisfied = resolveEvidenceChecklist(
      ['identity_proof'],
      {'aadhaar_card'}.toSet(),
    );
    expect(satisfied.single.status, EvidenceStatus.available);
    expect(satisfied.single.matchedDocumentType, 'aadhaar_card');
  });

  test('profile-info requirements route to profile, never upload', () {
    final mapping = evidenceMappingFor('income_tax_payer');
    expect(mapping, isNotNull);
    expect(mapping!.kind, EvidenceKind.profileInfo);
    expect(mapping.profilePrompt, 'Are you an income-tax payer?');
    expect(mapping.documentTypes, isEmpty);

    final items = resolveEvidenceChecklist(
      ['income_tax_payer'],
      {'aadhaar_card', 'bank_passbook'}.toSet(),
    );
    expect(items.single.kind, EvidenceKind.profileInfo);
    expect(items.single.status, EvidenceStatus.needed);
  });

  test('unsupported requirements are manual, never hidden', () {
    final items = resolveEvidenceChecklist(
      ['trader_license'],
      {'aadhaar_card'}.toSet(),
    );
    expect(items.single.kind, EvidenceKind.manual);
    expect(items.single.status, EvidenceStatus.manual);
    expect(items.single.note, contains('may be required'));
  });

  test('humanize never leaks raw snake_case keys', () {
    expect(
      humanizeEvidenceRequirement('income_tax_payer'),
      'Income-tax payer status',
    );
    expect(humanizeEvidenceRequirement('farmer_registration'), 'Farmer ID');
    expect(
      humanizeEvidenceRequirement('some_new_scheme_evidence'),
      isNot(contains('_')),
    );
  });

  test('evidence checklist JSON round-trips labels', () {
    final raw = <String, dynamic>{
      'requirement': 'land_record',
      'label': 'Land record',
      'kind': 'document',
      'status': 'needed',
      'document_types': ['land_document'],
      'matched_document_type': null,
    };
    final entry = EvidenceChecklistEntry.fromJson(raw);
    expect(entry.requirement, 'land_record');
    expect(entry.label, 'Land record');
    expect(entry.kind, EvidenceKind.document);
    expect(entry.status, EvidenceStatus.needed);
    expect(entry.documentTypes, ['land_document']);
  });

  test('backend verified and pending statuses are held evidence', () {
    final verified = EvidenceChecklistEntry.fromJson(const {
      'requirement': 'aadhaar',
      'label': 'Aadhaar',
      'kind': 'document',
      'status': 'verified',
      'document_types': ['aadhaar_card'],
      'matched_document_type': 'aadhaar_card',
    });
    final pending = EvidenceChecklistEntry.fromJson(const {
      'requirement': 'land_record',
      'label': 'Land record',
      'kind': 'document',
      'status': 'pending',
      'document_types': ['land_document'],
      'matched_document_type': 'land_document',
    });

    expect(verified.status, EvidenceStatus.verified);
    expect(verified.status.isHeld, isTrue);
    expect(pending.status, EvidenceStatus.pending);
    expect(pending.status.isHeld, isTrue);
  });
}
