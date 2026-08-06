# Module 4 Database Schema

Module 4 extends the backend with recommendation, eligibility, and feedback tables.

## Tables

### eligibility_rules

Stores the configurable rules used by the eligibility engine.

Key fields:
- `id`
- `code`
- `condition`
- `operator`
- `value`
- `priority`
- `description`
- `examples`
- `scope_type`
- `scope_value`
- `is_mandatory`
- `is_active`
- `created_at`
- `updated_at`

### recommendation_history

Stores each generated or refreshed recommendation request.

Key fields:
- `id`
- `citizen_id`
- `request_type`
- `query_text`
- `top_k`
- `total_candidates`
- `eligible_count`
- `overall_confidence`
- `status`
- `execution_time_ms`
- `context_snapshot`
- `notes`
- `created_at`
- `completed_at`
- `updated_at`

### eligibility_logs

Stores the audit trail for rule evaluation.

Key fields:
- `id`
- `citizen_id`
- `history_id`
- `scheme_id`
- `rule_id`
- `rule_code`
- `condition`
- `operator`
- `expected_value`
- `actual_value`
- `passed`
- `severity`
- `details`
- `created_at`

### recommendation_feedback

Stores post-recommendation citizen feedback.

Key fields:
- `id`
- `citizen_id`
- `history_id`
- `scheme_id`
- `rating`
- `is_helpful`
- `feedback_text`
- `status`
- `created_at`
- `updated_at`

### citizen_scheme_matches

Stores ranked recommendation results returned to the citizen.

Key fields:
- `id`
- `citizen_id`
- `history_id`
- `scheme_id`
- `scheme_name`
- `description`
- `benefits`
- `eligibility_status`
- `eligibility_percentage`
- `similarity_score`
- `confidence_score`
- `overall_score`
- `ranking_position`
- `recommendation_reason`
- `matched_rules`
- `missing_requirements`
- `required_documents`
- `estimated_benefit`
- `application_ready`
- `profile_match_percentage`
- `semantic_query`
- `created_at`
- `updated_at`

## Relationships

- One citizen can have many recommendation history records.
- One history record can have many eligibility logs and matches.
- One history record can have many feedback entries.
- Each match belongs to one scheme and one history record.

## Indexing Strategy

- Rule lookups are indexed by code, scope, priority, and active status.
- History queries are indexed by citizen and creation time.
- Logs are indexed by history, scheme, rule code, and pass/fail state.
- Match queries are indexed by citizen, scheme, ranking, and score.
- Feedback queries are indexed by citizen, history, scheme, and status.