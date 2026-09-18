import React, { useMemo } from 'react';
import ParamGroup from './ParamGroup.jsx';
import SingleSelect from './SingleSelect.jsx';
import MultiSelect from './MultiSelect.jsx';

// Static option dicts (mirror bod_app.data.params).
const ENCOUNTER_WINDOWS = { '1': '30-day window', '2': '90-day window' };
const GRANULARITIES     = { '1': 'National', '2': 'Region', '3': 'State', '4': 'MSA' };
const TIME_LEVELS       = { month: 'Monthly', quarter: 'Quarterly', year: 'Yearly' };

/**
 * Two-row Tableau-style filter panel — no global Apply button.
 *
 * Interaction:
 *   - **Single-select filters** (radio popovers) fire `applyFilters(next)`
 *     immediately on selection change.
 *   - **Multi-select filters** buffer their edits in a local draft inside
 *     the popover; the popover has its own Apply / Cancel buttons that
 *     commit or discard the draft.
 *   - The Reset button restores DEFAULT_FILTERS and re-applies.
 */
export default function FilterPanel({ filters, setFilters, applyFilters, options, dateExtents, onReset }) {
  const monthOptions = useMemo(() => buildMonthOptions(dateExtents), [dateExtents]);
  const yearOptions  = options.years || [];

  // Single-select helper — updates the store AND fires a data refresh.
  const bindSingle = (key) => ({
    value: filters[key],
    onChange: (v) => {
      const next = { ...filters, [key]: v };
      setFilters(next);
      applyFilters(next);
    },
  });

  // Multi-select helper — the MultiSelect popover buffers edits internally
  // and calls `onChange` only when the user clicks Apply. So we still fire
  // `applyFilters` here on every commit.
  const bindMulti = (key) => ({
    value: filters[key],
    onChange: (v) => {
      const next = { ...filters, [key]: v };
      setFilters(next);
      applyFilters(next);
    },
  });

  return (
    <div className="param-panel">
      <div className="param-row">
        <ParamGroup title="General Parameters" flex={8}>
          <SingleSelect id="p-time-level"       label="Time Frequency"
            options={TIME_LEVELS} {...bindSingle('time_level')} />
          <MultiSelect  id="p-year"             label="Year"
            options={yearOptions} value={filters._yearSel || []}
            onChange={(v) => {
              const next = { ...filters, _yearSel: v };
              setFilters(next);
              applyFilters(next);
            }} />
          <SingleSelect id="p-start-month"      label="Start Month"
            options={monthOptions} {...bindSingle('start_month')} />
          <SingleSelect id="p-end-month"        label="End Month"
            options={monthOptions} {...bindSingle('end_month')} />
          <SingleSelect id="p-granularity"      label="Select Granularity"
            options={GRANULARITIES} {...bindSingle('granularity')} />
          <MultiSelect  id="p-granularity-value" label="Select Granularity Value"
            options={options['p-granularity-value'] || []} {...bindMulti('granularity_value')} />
          <SingleSelect id="p-encounter-window" label="Follow-up Visit Window"
            options={ENCOUNTER_WINDOWS} {...bindSingle('encounter_window')} />
        </ParamGroup>
        <ParamGroup title="Patient Parameters" flex={4}>
          <MultiSelect id="f-age-group"    label="Age Group"
            options={options['f-age-group']    || []} {...bindMulti('age_group')} />
          <MultiSelect id="f-gender"       label="Gender"
            options={options['f-gender']       || []} {...bindMulti('patient_gender')} />
          <MultiSelect id="f-payer"        label="Payer Channel"
            options={options['f-payer']        || []} {...bindMulti('payer_type')} />
          <MultiSelect id="f-hr-condition" label="High Risk Condition"
            options={options['f-hr-condition'] || []} {...bindMulti('hr_condition')} />
        </ParamGroup>
      </div>
      <div className="param-row">
        <ParamGroup title="Account/HCP Parameters" flex={1}>
          <MultiSelect id="f-grouped-account" label="Grouped Accounts"
            options={options['f-grouped-account'] || []} {...bindMulti('grouped_account')} />
          <MultiSelect id="f-parent-id"       label="Parent Account"
            options={options['f-parent-id']       || []} {...bindMulti('parent_id')} />
          <MultiSelect id="f-child-id"        label="Child Account"
            options={options['f-child-id']        || []} {...bindMulti('child_id')} />
          <MultiSelect id="f-specialty-group" label="Specialty Group"
            options={options['f-specialty-group'] || []} {...bindMulti('specialty_group')} />
          <MultiSelect id="f-specialty"       label="Primary Specialty"
            options={options['f-specialty']       || []} {...bindMulti('hcp_primary_specialty')} />
          <MultiSelect id="f-area"            label="Area Type"
            options={options['f-area']            || []} {...bindMulti('area_type')} />
        </ParamGroup>
        <div className="param-actions" style={actionsColStyle}>
          <button className="reset-btn"
                  title="Reset filters"
                  onClick={onReset}
                  style={resetBtnStyle}>&#8635;</button>
        </div>
      </div>
    </div>
  );
}

const actionsColStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'stretch',
  justifyContent: 'stretch',
  minWidth: 60,
};

const resetBtnStyle = {
  flex: 1,           // fills the vertical space that Apply used to occupy
  minHeight: 56,
  fontSize: 22,
  lineHeight: 1,
  background: 'transparent',
  color: '#000',
  border: '1px solid #B8B8B8',
  cursor: 'pointer',
};

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
