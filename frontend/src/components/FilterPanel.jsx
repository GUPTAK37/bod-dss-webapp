import React, { useMemo } from 'react';
import ParamGroup from './ParamGroup.jsx';
import SingleSelect from './SingleSelect.jsx';
import MultiSelect from './MultiSelect.jsx';

// Static option dicts (mirror bod_app.data.params).
const ENCOUNTER_WINDOWS = { '1': '30-day window', '2': '90-day window' };
const GRANULARITIES     = { '1': 'National', '2': 'Region', '3': 'State', '4': 'MSA' };
const TIME_LEVELS       = { month: 'Monthly', quarter: 'Quarterly', year: 'Yearly' };

/**
 * Two-row Tableau-style filter panel:
 *   Row 1: General Parameters (wide) + Patient Parameters
 *   Row 2: Account/HCP Parameters + Apply/Reset buttons
 */
export default function FilterPanel({ filters, setFilters, options, dateExtents, onApply, onReset }) {
  const monthOptions = useMemo(() => buildMonthOptions(dateExtents), [dateExtents]);
  const yearOptions  = options.years || [];

  const bind = (key) => ({
    value: filters[key],
    onChange: (v) => setFilters({ ...filters, [key]: v }),
  });

  return (
    <div className="param-panel">
      <div className="param-row">
        <ParamGroup title="General Parameters" flex={8}>
          <SingleSelect id="p-time-level"       label="Time Frequency"
            options={TIME_LEVELS} {...bind('time_level')} />
          <MultiSelect  id="p-year"             label="Year"
            options={yearOptions} value={filters._yearSel || []}
            onChange={(v) => setFilters({ ...filters, _yearSel: v })} />
          <SingleSelect id="p-start-month"      label="Start Month"
            options={monthOptions} {...bind('start_month')} />
          <SingleSelect id="p-end-month"        label="End Month"
            options={monthOptions} {...bind('end_month')} />
          <SingleSelect id="p-granularity"      label="Select Granularity"
            options={GRANULARITIES} {...bind('granularity')} />
          <MultiSelect  id="p-granularity-value" label="Select Granularity Value"
            options={options['p-granularity-value'] || []} {...bind('granularity_value')} />
          <SingleSelect id="p-encounter-window" label="Follow-up Visit Window"
            options={ENCOUNTER_WINDOWS} {...bind('encounter_window')} />
        </ParamGroup>
        <ParamGroup title="Patient Parameters" flex={4}>
          <MultiSelect id="f-age-group"    label="Age Group"
            options={options['f-age-group']    || []} value={filters.age_group}
            onChange={(v) => setFilters({ ...filters, age_group: v })} />
          <MultiSelect id="f-gender"       label="Gender"
            options={options['f-gender']       || []} value={filters.patient_gender}
            onChange={(v) => setFilters({ ...filters, patient_gender: v })} />
          <MultiSelect id="f-payer"        label="Payer Channel"
            options={options['f-payer']        || []} value={filters.payer_type}
            onChange={(v) => setFilters({ ...filters, payer_type: v })} />
          <MultiSelect id="f-hr-condition" label="High Risk Condition"
            options={options['f-hr-condition'] || []} value={filters.hr_condition}
            onChange={(v) => setFilters({ ...filters, hr_condition: v })} />
        </ParamGroup>
      </div>
      <div className="param-row">
        <ParamGroup title="Account/HCP Parameters" flex={1}>
          <MultiSelect id="f-grouped-account" label="Grouped Accounts"
            options={options['f-grouped-account'] || []} value={filters.grouped_account}
            onChange={(v) => setFilters({ ...filters, grouped_account: v })} />
          <MultiSelect id="f-parent-id"       label="Parent Account"
            options={options['f-parent-id']       || []} value={filters.parent_id}
            onChange={(v) => setFilters({ ...filters, parent_id: v })} />
          <MultiSelect id="f-child-id"        label="Child Account"
            options={options['f-child-id']        || []} value={filters.child_id}
            onChange={(v) => setFilters({ ...filters, child_id: v })} />
          <MultiSelect id="f-specialty-group" label="Specialty Group"
            options={options['f-specialty-group'] || []} value={filters.specialty_group}
            onChange={(v) => setFilters({ ...filters, specialty_group: v })} />
          <MultiSelect id="f-specialty"       label="Primary Specialty"
            options={options['f-specialty']       || []} value={filters.hcp_primary_specialty}
            onChange={(v) => setFilters({ ...filters, hcp_primary_specialty: v })} />
          <MultiSelect id="f-area"            label="Area Type"
            options={options['f-area']            || []} value={filters.area_type}
            onChange={(v) => setFilters({ ...filters, area_type: v })} />
        </ParamGroup>
        <div className="param-actions">
          <button className="apply-btn" onClick={onApply}>Apply Filters</button>
          <button className="reset-btn" title="Reset filters" onClick={onReset}>&#8635;</button>
        </div>
      </div>
    </div>
  );
}

function buildMonthOptions(extents) {
  if (!extents?.min_date || !extents?.max_date) return {};
  const min = new Date(extents.min_date);
  const max = new Date(extents.max_date);
  const out = {};
  const d = new Date(min.getFullYear(), min.getMonth(), 1);
  while (d <= max) {
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
    const label = d.toLocaleString('en-US', { month: 'short' }) + ` '${String(d.getFullYear()).slice(-2)}`;
    out[iso] = label;
    d.setMonth(d.getMonth() + 1);
  }
  return out;
}
