import React from 'react';
import SingleSelect from './SingleSelect.jsx';
import MultiSelect from './MultiSelect.jsx';

/**
 * Local per-section filter shelves — S8 (VISIT, HR grouping, Top-7 items) and
 * S10 (VISIT multi-select). Mirrors _hr_local_filters / _s10_local_filters
 * from bod_app.
 */
export default function LocalFilters({ kind, filters, setFilters, options, hrDyn }) {
  if (kind === 's8') {
    const visitOpts = options['s8-visit-filter'] || [];
    const hrGroupingOpts = hrDyn?.hr_grouping_options || [];
    const top7Opts = hrDyn?.top7_options || [];
    return (
      <>
        <SingleSelect
          id="s8-visit-filter"
          label="VISIT"
          options={visitOpts}
          value={filters.s8_visit_types?.[0] || 'ED VISIT'}
          onChange={(v) => setFilters({ ...filters, s8_visit_types: v ? [v] : [] })}
          className="local-filter-btn"
          labelClass="local-filter-label"
        />
        <MultiSelect
          id="s8-hr-filter"
          label="High Risk Conditions"
          options={hrGroupingOpts}
          value={filters.s8_hr_conditions}
          onChange={(v) => setFilters({ ...filters, s8_hr_conditions: v })}
          className="local-filter-btn"
          labelClass="local-filter-label"
        />
        <MultiSelect
          id="s8-top7-items"
          label="Top 7 HR Conditions"
          options={top7Opts}
          value={filters.s8_top7_items}
          onChange={(v) => setFilters({ ...filters, s8_top7_items: v })}
          className="local-filter-btn"
          labelClass="local-filter-label"
        />
      </>
    );
  }
  if (kind === 's10') {
    return (
      <MultiSelect
        id="s10-visit-filter"
        label="VISIT"
        options={options['s10-visit-filter'] || []}
        value={filters.s10_visit_types}
        onChange={(v) => setFilters({ ...filters, s10_visit_types: v })}
        className="local-filter-btn"
        labelClass="local-filter-label"
      />
    );
  }
  return null;
}
