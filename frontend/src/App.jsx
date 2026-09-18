import React, { useEffect, useState, useCallback } from 'react';
import AppHeader from './components/AppHeader.jsx';
import FilterPanel from './components/FilterPanel.jsx';
import Section from './components/Section.jsx';
import LoadingOverlay from './components/LoadingOverlay.jsx';
import { SECTIONS } from './sections.config.js';
import { DEFAULT_FILTERS } from './state/store.js';
import { getFilterOptions, postFilterCascade, postHrTop7 } from './api';

/**
 * Root of the SPA.
 *
 * Loading state (surfaced via LoadingOverlay while Apply is running):
 *   - `filtersPhase`: 'idle' | 'initial' | 'cascade' | 'sections'
 *   - `sectionsPending`: Set of section ids currently fetching
 * Together they drive the 3-step overlay:
 *     1. Loading filter data
 *     2. Refreshing filter options
 *     3. Refreshing charts (N of 10)
 */
export default function App() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [options, setOptions] = useState({});
  const [dateExtents, setDateExtents] = useState({});
  const [hrDyn, setHrDyn] = useState(null);
  const [filtersVersion, setFiltersVersion] = useState(0);

  const [filtersPhase, setFiltersPhase] = useState('initial');
  const [sectionsPending, setSectionsPending] = useState(new Set());

  const notifySectionStart = useCallback((sid) => {
    setSectionsPending((prev) => {
      const next = new Set(prev);
      next.add(sid);
      return next;
    });
  }, []);
  const notifySectionEnd = useCallback((sid) => {
    setSectionsPending((prev) => {
      const next = new Set(prev);
      next.delete(sid);
      return next;
    });
  }, []);

  useEffect(() => {
    setFiltersPhase('initial');
    getFilterOptions()
      .then((r) => {
        setDateExtents({ min_date: r.min_date, max_date: r.max_date });
        setOptions({ ...(r.filters || {}), years: r.years || [] });
      })
      .catch((e) => console.error('filter-options failed', e))
      .finally(() => setFiltersPhase('idle'));
  }, []);

  const onApply = async () => {
    setFiltersPhase('cascade');
    // 1. Cascade update for downstream filter option lists.
    try {
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
        granularity: filters.granularity, selections, currents: {},
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
    setFiltersPhase('sections');
    setSectionsPending(new Set(SECTIONS.map((s) => s.id)));
    setFiltersVersion((v) => v + 1);
  };

  // When all sections have reported back, drop the overlay.
  useEffect(() => {
    if (filtersPhase === 'sections' && sectionsPending.size === 0) {
      setFiltersPhase('idle');
    }
  }, [filtersPhase, sectionsPending]);

  const onReset = () => {
    setFilters(DEFAULT_FILTERS);
    setFiltersPhase('sections');
    setSectionsPending(new Set(SECTIONS.map((s) => s.id)));
    setFiltersVersion((v) => v + 1);
  };

  // Build the overlay's 3-step spec.
  const totalSections = SECTIONS.length;
  const doneSections = totalSections - sectionsPending.size;
  const overlay = buildOverlaySteps(filtersPhase, doneSections, totalSections);

  return (
    <div>
      <LoadingOverlay
        visible={filtersPhase !== 'idle'}
        title={filtersPhase === 'initial' ? 'Opening workbook' : 'Applying filters'}
        steps={overlay}
      />
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
            onLoadStart={notifySectionStart}
            onLoadEnd={notifySectionEnd}
          />
        ))}
      </div>
    </div>
  );
}

function buildOverlaySteps(phase, done, total) {
  if (phase === 'initial') {
    return [
      { label: 'Loading filter options', status: 'active' },
      { label: 'Refreshing charts',       status: 'pending' },
    ];
  }
  // Apply-flow: cascade → sections
  const cascadeStatus =
    phase === 'cascade' ? 'active'
    : phase === 'sections' ? 'done'
    : 'pending';
  const sectionsStatus =
    phase === 'sections'
      ? (done >= total ? 'done' : 'active')
      : 'pending';

  const chartsLabel =
    phase === 'sections' && total > 0
      ? `Refreshing charts (${done} / ${total})`
      : 'Refreshing charts';

  return [
    { label: 'Refreshing filter options', status: cascadeStatus },
    { label: chartsLabel,                 status: sectionsStatus },
  ];
}
