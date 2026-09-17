// Default `BoDFilters.to_store()` shape — must stay 1:1 with the backend.
export const DEFAULT_FILTERS = {
  encounter_window: '1',
  metric_mode: 2.0,
  granularity: '3',
  granularity_value: [],
  start_month: '2025-08-01',
  end_month: '2026-07-01',
  time_level: 'quarter',
  reference_line: 'No',
  hr_condition: [],
  age_group: [],
  patient_gender: [],
  payer_type: [],
  area_type: [],
  region: [],
  state: [],
  msa: [],
  hcp_primary_specialty: [],
  specialty_group: [],
  parent_id: [],
  child_id: [],
  grouped_account: [],
  s8_visit_types: ['ED VISIT'],
  s8_hr_conditions: ['Top 7 HR Conditions'],
  s8_top7_items: [],
  s8_top_n: 7,
  s10_visit_types: [],
};

// Mapping from filter-id (used by cascade endpoint) → BoDFilters store key.
// Store keys use snake_case; filter IDs mirror the Dash IDs for API parity.
export const FID_TO_STORE_KEY = {
  'f-age-group': 'age_group',
  'f-gender': 'patient_gender',
  'f-payer': 'payer_type',
  'f-hr-condition': 'hr_condition',
  'f-grouped-account': 'grouped_account',
  'f-parent-id': 'parent_id',
  'f-child-id': 'child_id',
  'f-specialty-group': 'specialty_group',
  'f-specialty': 'hcp_primary_specialty',
  'f-area': 'area_type',
  'p-granularity-value': 'granularity_value',
  // p-year is UI-only; the store uses start_month/end_month directly.
};
