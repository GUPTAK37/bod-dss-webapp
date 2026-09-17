import React, { useEffect, useState } from 'react';
import AppHeader from './components/AppHeader.jsx';
import FilterPanel from './components/FilterPanel.jsx';
import Section from './components/Section.jsx';
import { SECTIONS } from './sections.config.js';
import { DEFAULT_FILTERS } from './state/store.js';
import { getFilterOptions, postFilterCascade, postHrTop7 } from './api';

/**
 * Root of the SPA.
 *
 * Data flow:
 *   1. On mount, hit /api/filter-options — populates every dropdown's option
 *      list, min/max dates, and available years.
 *   2. `filters` is the working state (mirrors bod_app's dcc.Store).
 *   3. Clicking "Apply Filters" bumps `filtersVersion`; every Section
 *      component `useEffect`s on that and re-fetches its data.
 *   4. Apply also fires a cascade (Only-Relevant Values) and an S8 Top-7
 *      refresh so downstream dropdown option lists follow the workbook.
 */
export default function App() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [options, setOptions] = useState({});
  const [dateExtents, setDateExtents] = useState({});
  const [hrDyn, setHrDyn] = useState(null);
  const [filtersVersion, setFiltersVersion] = useState(0);

  useEffect(() => {
    getFilterOptions()
      .then((r) => {
        setDateExtents({ min_date: r.min_date, max_date: r.max_date });
        setOptions({ ...(r.filters || {}), years: r.years || [] });
      })
      .catch((e) => console.error('filter-options failed', e));
  }, []);

  const onApply = async () => {
    // 1. Cascade update for downstream filter option lists.
    try {
      const currents = {}; // We don't currently track __ALL__ sentinels; leave empty.
      const selections = {
        'f-age-group': filters.age_group,
        'f-gender':    filters.patient_gender,
        'f-payer':     filters.payer_type,
        'f-hr-condition': filters.hr_condition,
        'f-grouped-account': filters.grouped_account,
        'f-parent-id': filters.parent_id,
        'f-child-id':  filters.child_id,
        'f-specialty-group': filters.specialty_group,
        'f-specialty': filters.hcp_primary_specialty,
        'f-area':      filters.area_type,
        'p-granularity-value': filters.granularity_value,
      };
      const cascade = await postFilterCascade({
        granularity: filters.granularity, selections, currents,
      });
      setOptions((prev) => {
        const next = { ...prev };
        Object.entries(cascade).forEach(([fid, spec]) => { next[fid] = spec.options; });
        return next;
      });
    } catch (e) { console.warn('cascade failed', e); }

    // 2. S8 Top-7 dynamic options.
    try {
      const dyn = await postHrTop7(filters);
      setHrDyn(dyn);
    } catch (e) { console.warn('hr-top7 failed', e); }

    // 3. Trigger every section to refetch.
    setFiltersVersion((v) => v + 1);
  };

  const onReset = () => {
    setFilters(DEFAULT_FILTERS);
    setFiltersVersion((v) => v + 1);
  };

  return (
    <div>
      <AppHeader />
      <FilterPanel
        filters={filters}
        setFilters={setFilters}
        options={options}
        dateExtents={dateExtents}
        onApply={onApply}
        onReset={onReset}
      />
      <div className="sections-wrap">
        {SECTIONS.map((cfg) => (
          <Section
            key={cfg.id}
            config={cfg}
            filters={filters}
            filtersVersion={filtersVersion}
            options={options}
            hrDyn={hrDyn}
            setFilters={setFilters}
          />
        ))}
      </div>
    </div>
  );
}
