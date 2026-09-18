import React, { useEffect, useState } from 'react';
import PlotlyChart from './PlotlyChart.jsx';
import DataTable from './DataTable.jsx';
import LocalFilters from './LocalFilters.jsx';
import { fetchSection } from '../api';

/**
 * A single dashboard section — blue title bar, optional local filters, sub-
 * header pills (Time Period / Window / #Episodes), Plotly chart, HTML table.
 * Fires POST /api/section/<id> whenever `filtersVersion` changes.
 */
export default function Section({ config, filters, filtersVersion, options, hrDyn, setFilters, onLoadStart, onLoadEnd }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (filtersVersion === 0) return; // wait for the first Apply
    let alive = true;
    setLoading(true); setError(null);
    onLoadStart?.(config.id);
    fetchSection(config.id, filters)
      .then((r) => { if (alive) setData(r); })
      .catch((e) => { if (alive) setError(String(e.message || e)); })
      .finally(() => {
        if (alive) setLoading(false);
        onLoadEnd?.(config.id);
      });
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filtersVersion]);

  return (
    <div className="section-card">
      <div className="section-title">
        <div className="section-title-text">{config.title}</div>
        {config.localFilters && (
          <div className="section-local-filters-inline">
            <LocalFilters
              kind={config.localFilters}
              filters={filters}
              setFilters={setFilters}
              options={options}
              hrDyn={hrDyn}
            />
          </div>
        )}
      </div>
      <div className="section-sub-row">
        <div className="section-sub">{data?.subheader?.timeperiod || ''}</div>
        <div className="section-sub">{data?.subheader?.window || ''}</div>
        <div className="section-sub section-sub-strong">
          {(data?.subheader?.episodes || []).map((line, i) => <div key={i}>{line}</div>)}
        </div>
      </div>
      <div className="section-body">
        {config.legend && (
          <div className="bod-legend">
            {config.legend.map((l, i) => (
              <div key={i} className="legend-item">
                <span className="legend-swatch" style={{ background: l.color }} />
                <span className="legend-label">{l.label}</span>
              </div>
            ))}
          </div>
        )}
        <div className="bod-chart-wrap" style={{ position: 'relative' }}>
          {loading && <div style={loadingStyle}>Loading…</div>}
          {error && <div className="err">Error: {error}</div>}
          <PlotlyChart figure={data?.figure} height={config.chartHeight || 300} />
        </div>
        <div className="bod-table">
          <DataTable table={data?.table} />
        </div>
      </div>
    </div>
  );
}

const loadingStyle = {
  position: 'absolute', top: 4, right: 8, fontSize: 10, color: '#888',
};
