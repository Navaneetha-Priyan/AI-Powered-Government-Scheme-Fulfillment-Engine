/// Central evidence mapping, mirrors backend service.
library;
import '../constants/document_types.dart';
enum EvidenceKind { document, profileInfo, manual }
enum EvidenceStatus { available, verified, pending, needed, manual }
extension EvidenceStatusX on EvidenceStatus {
  bool get isHeld =>
      this == EvidenceStatus.available ||
      this == EvidenceStatus.verified ||
      this == EvidenceStatus.pending;
}
class EvidenceMapping {
  const EvidenceMapping({required this.requirement, required this.label,
    required this.kind, this.documentTypes = const [], this.profileField,
    this.profilePrompt, this.note});
  final String requirement; final String label; final EvidenceKind kind;
  final List<String> documentTypes; final String? profileField;
  final String? profilePrompt; final String? note;
}
const Set<String> kSupportedUploadDocumentTypes = {
  DocumentTypes.aadhaar, DocumentTypes.smartRation,
  DocumentTypes.incomeCertificate, DocumentTypes.communityCertificate,
  DocumentTypes.landRecord, DocumentTypes.farmerDocument,
  DocumentTypes.disabilityCertificate, DocumentTypes.bankPassbook,
  DocumentTypes.educationCertificate,
};
const Map<String, EvidenceMapping> kDocumentEvidenceMappings = {
  'aadhaar': EvidenceMapping(requirement: 'aadhaar', label: 'Aadhaar',
      kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.aadhaar]),
  'identity_proof': EvidenceMapping(requirement: 'identity_proof',
      label: 'Identity proof', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.aadhaar]),
  'address_proof': EvidenceMapping(requirement: 'address_proof',
      label: 'Residence proof', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.aadhaar, DocumentTypes.smartRation]),
  'bank_account': EvidenceMapping(requirement: 'bank_account',
      label: 'Bank account proof', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.bankPassbook]),
  'bank_passbook': EvidenceMapping(requirement: 'bank_passbook',
      label: 'Bank account proof', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.bankPassbook]),
  'land_record': EvidenceMapping(requirement: 'land_record',
      label: 'Land record', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.landRecord],
      note: 'Land record / patta proves ownership.'),
  'land_ownership_proof': EvidenceMapping(
      requirement: 'land_ownership_proof', label: 'Land ownership proof',
      kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.landRecord],
      note: 'Land record / patta proves ownership.'),
  'farmer_id': EvidenceMapping(requirement: 'farmer_id', label: 'Farmer ID',
      kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.farmerDocument]),
  'farmer_registration': EvidenceMapping(requirement: 'farmer_registration',
      label: 'Farmer ID', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.farmerDocument]),
  'community_certificate': EvidenceMapping(
      requirement: 'community_certificate', label: 'Community certificate',
      kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.communityCertificate]),
  'caste_certificate': EvidenceMapping(requirement: 'caste_certificate',
      label: 'Community certificate', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.communityCertificate]),
  'income_proof': EvidenceMapping(requirement: 'income_proof',
      label: 'Income proof', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.incomeCertificate]),
  'income_certificate': EvidenceMapping(requirement: 'income_certificate',
      label: 'Income proof', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.incomeCertificate]),
  'disability_certificate': EvidenceMapping(
      requirement: 'disability_certificate', label: 'Disability certificate',
      kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.disabilityCertificate]),
  'ration_card': EvidenceMapping(requirement: 'ration_card',
      label: 'Ration card', kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.smartRation]),
  'education_certificate': EvidenceMapping(
      requirement: 'education_certificate', label: 'Education certificate',
      kind: EvidenceKind.document,
      documentTypes: [DocumentTypes.educationCertificate]),
};
const Map<String, EvidenceMapping> kProfileEvidenceMappings = {
  'income_tax_payer': EvidenceMapping(requirement: 'income_tax_payer',
      label: 'Income-tax payer status', kind: EvidenceKind.profileInfo,
      profileField: 'income_tax_payer',
      profilePrompt: 'Are you an income-tax payer?'),
  'government_employee_status': EvidenceMapping(
      requirement: 'government_employee_status',
      label: 'Government employment status', kind: EvidenceKind.profileInfo,
      profileField: 'government_employee_status',
      profilePrompt: 'Are you a government employee?'),
  'professional_category': EvidenceMapping(
      requirement: 'professional_category', label: 'Professional category',
      kind: EvidenceKind.profileInfo, profileField: 'professional_category',
      profilePrompt: 'What is your professional category?'),
  'pension_amount': EvidenceMapping(requirement: 'pension_amount',
      label: 'Pension amount', kind: EvidenceKind.profileInfo,
      profileField: 'pension_amount',
      profilePrompt: 'What pension amount do you receive?'),
  'street_vendor_proof': EvidenceMapping(requirement: 'street_vendor_proof',
      label: 'Street vendor record', kind: EvidenceKind.profileInfo,
      profileField: 'street_vendor_status',
      profilePrompt: 'Are you registered as a street vendor?'),
  'pregnancy_status': EvidenceMapping(requirement: 'pregnancy_status',
      label: 'Pregnancy status', kind: EvidenceKind.profileInfo,
      profileField: 'pregnancy_status',
      profilePrompt: 'Are you currently pregnant?'),
  'child_age': EvidenceMapping(requirement: 'child_age', label: 'Child age',
      kind: EvidenceKind.profileInfo, profileField: 'child_age',
      profilePrompt: "What is the child's age?"),
  'annual_income': EvidenceMapping(requirement: 'annual_income',
      label: 'Annual income', kind: EvidenceKind.profileInfo,
      profileField: 'annual_income',
      profilePrompt: 'What is your annual income?'),
};
EvidenceMapping? evidenceMappingFor(String requirement) {
  final key = requirement.trim().toLowerCase();
  return kDocumentEvidenceMappings[key] ?? kProfileEvidenceMappings[key];
}
String humanizeEvidenceRequirement(String requirement) {
  final mapping = evidenceMappingFor(requirement);
  if (mapping != null) return mapping.label;
  final text = requirement.replaceAll('_', ' ').trim();
  if (text.isEmpty) return 'Requirement';
  return text.split(' ').map((w) => w.isEmpty ? w :
      '${w[0].toUpperCase()}${w.substring(1)}').join(' ');
}
class EvidenceChecklistEntry {
  const EvidenceChecklistEntry({required this.requirement,
    required this.label, required this.kind, required this.status,
    this.documentTypes = const [], this.matchedDocumentType,
    this.profileField, this.profilePrompt, this.note});
  final String requirement; final String label; final EvidenceKind kind;
  final EvidenceStatus status; final List<String> documentTypes;
  final String? matchedDocumentType; final String? profileField;
  final String? profilePrompt; final String? note;
  factory EvidenceChecklistEntry.fromJson(Map<String, dynamic> json) {
    EvidenceKind kind;
    switch (json['kind']?.toString()) {
      case 'profile_info': kind = EvidenceKind.profileInfo; break;
      case 'manual': kind = EvidenceKind.manual; break;
      default: kind = EvidenceKind.document;
    }
    EvidenceStatus status;
    switch (json['status']?.toString()) {
      case 'available': status = EvidenceStatus.available; break;
      case 'verified': status = EvidenceStatus.verified; break;
      case 'pending': status = EvidenceStatus.pending; break;
      case 'manual': status = EvidenceStatus.manual; break;
      default: status = EvidenceStatus.needed;
    }
    return EvidenceChecklistEntry(
      requirement: json['requirement']?.toString() ?? '',
      label: json['label']?.toString() ?? humanizeEvidenceRequirement(
          json['requirement']?.toString() ?? ''),
      kind: kind, status: status,
      documentTypes: (json['document_types'] as List? ?? const [])
          .map((e) => e.toString()).toList(),
      matchedDocumentType: json['matched_document_type']?.toString(),
      profileField: json['profile_field']?.toString(),
      profilePrompt: json['profile_prompt']?.toString(),
      note: json['note']?.toString());
  }
}
List<EvidenceChecklistEntry> resolveEvidenceChecklist(
    Iterable<String> requirements, Set<String> uploadedDocumentTypes,
    {Set<String>? missingOnly}) {
  final seen = <String>[];
  for (final raw in requirements) {
    final key = raw.trim().toLowerCase();
    if (key.isNotEmpty && !seen.contains(key)) seen.add(key);
  }
  final missing = missingOnly?.map((e) => e.trim().toLowerCase()).toSet();
  final uploaded = uploadedDocumentTypes.map((e) => e.toLowerCase()).toSet();
  return seen.map((key) {
    final mapping = evidenceMappingFor(key);
    if (mapping == null) {
      return EvidenceChecklistEntry(requirement: key,
        label: humanizeEvidenceRequirement(key), kind: EvidenceKind.manual,
        status: EvidenceStatus.manual,
        note: 'Additional scheme-specific evidence may be required.');
    }
    if (mapping.kind == EvidenceKind.profileInfo) {
      final isMissing = missing == null || missing.contains(key);
      return EvidenceChecklistEntry(requirement: key, label: mapping.label,
        kind: EvidenceKind.profileInfo,
        status: isMissing ? EvidenceStatus.needed : EvidenceStatus.available,
        profileField: mapping.profileField,
        profilePrompt: mapping.profilePrompt);
    }
    String? matched;
    for (final doc in mapping.documentTypes) {
      if (uploaded.contains(doc.toLowerCase())) { matched = doc; break; }
    }
    EvidenceStatus status;
    if (missing != null && !missing.contains(key)) {
      status = matched != null ? EvidenceStatus.available : EvidenceStatus.manual;
    } else {
      status = matched != null ? EvidenceStatus.available : EvidenceStatus.needed;
    }
    return EvidenceChecklistEntry(requirement: key, label: mapping.label,
      kind: EvidenceKind.document, status: status,
      documentTypes: mapping.documentTypes, matchedDocumentType: matched,
      note: mapping.note);
  }).toList();
}

