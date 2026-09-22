import React, { useCallback, useEffect, useRef, useState } from 'react';
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
 * No global "Apply Filters" button:
 *   - Single-select changes commit immediately (radio popover in each filter).
 *   - Multi-select changes commit when the user clicks Apply *inside* that
 *     filter's popover.
 *   - Reset restores defaults and re-runs the full flow.
 *   - On first mount, the flow runs automatically with the default filters
 *     so the dashboard is populated without any click.
 *
 * Data flow per commit (`applyFilters(next)`):
 *   1. cascade  — POST /api/filter-cascade → refresh downstream option lists
 *   2. hr-top7  — POST /api/hr-top7        → refresh S8 dynamic options
 *   3. sections — bump `filtersVersion`     → every Section re-fetches
 * The LoadingOverlay tracks all three phases live.
 */
export default function App() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [options, setOptions] = useState({});
  const [dateExtents, setDateExtents] = useState({});
  const [hrDyn, setHrDyn] = useState(null);
  const [filtersVersion, setFiltersVersion] = useState(0);

  const [filtersPhase, setFiltersPhase] = useState('initial');
  const [sectionsPending, setSectionsPending] = useState(new Set());
  const bootstrappedRef = useRef(false);

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

  // Central "commit filters and refresh everything" function.
  // `nextFilters` is the fresh filter object (state may still be stale in
  // the caller's closure — we accept it explicitly to avoid that trap).
  const applyFilters = useCallback(async (nextFilters) => {
    setFiltersPhase('cascade');

    // 1. Cascade — refresh downstream filter option lists.
    try {
      const selections = {
        'f-age-group': nextFilters.age_group,
        'f-gender':    nextFilters.patient_gender,
        'f-payer':     nextFilters.payer_type,
        'f-hr-condition': nextFilters.hr_condition,
        'f-grouped-account': nextFilters.grouped_account,
        'f-parent-id': nextFilters.parent_id,
        'f-child-id':  nextFilters.child_id,
        'f-specialty-group': nextFilters.specialty_group,
        'f-specialty': nextFilters.hcp_primary_specialty,
        'f-area':      nextFilters.area_type,
        'p-granularity-value': nextFilters.granularity_value,
      };
      const cascade = await postFilterCascade({
        granularity: nextFilters.granularity, selections, currents: {},
      });
      setOptions((prev) => {
        const upd = { ...prev };
        Object.entries(cascade).forEach(([fid, spec]) => { upd[fid] = spec.options; });
        return upd;
      });
    } catch (e) { console.warn('cascade failed', e); }

    // 2. S8 Top-7 dynamic options.
    try {
      const dyn = await postHrTop7(nextFilters);
      setHrDyn(dyn);
    } catch (e) { console.warn('hr-top7 failed', e); }

    // 3. Kick every section to refetch.
    setFiltersPhase('sections');
    setSectionsPending(new Set(SECTIONS.map((s) => s.id)));
    setFiltersVersion((v) => v + 1);
  }, []);

  // -------- Initial bootstrap: load option lists, then auto-apply. ----------
  useEffect(() => {
    if (bootstrappedRef.current) return;
    bootstrappedRef.current = true;

    setFiltersPhase('initial');
    (async () => {
      try {
        const r = await getFilterOptions();
        setDateExtents({ min_date: r.min_date, max_date: r.max_date });
        setOptions({ ...(r.filters || {}), years: r.years || [] });
      } catch (e) {
        console.error('filter-options failed', e);
      }
      // Auto-apply with the defaults so the dashboard is populated on load.
      await applyFilters(DEFAULT_FILTERS);
    })();
  }, [applyFilters]);

  // Drop the overlay once every section has responded.
  useEffect(() => {
    if (filtersPhase === 'sections' && sectionsPending.size === 0) {
      setFiltersPhase('idle');
    }
  }, [filtersPhase, sectionsPending]);

  const onReset = () => {
    setFilters(DEFAULT_FILTERS);
    applyFilters(DEFAULT_FILTERS);
  };

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
        applyFilters={applyFilters}
        options={options}
        dateExtents={dateExtents}
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
            applyFilters={applyFilters}
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
