import React from 'react';
import Plot from 'react-plotly.js';

/**
 * Wraps react-plotly.js so a section can pass the raw JSON returned by
 * `fig.to_plotly_json()` on the backend.
 *
 * All click/drag interactions are disabled — the workbook is a static
 * dashboard, not an interactive exploration tool. Users only see tooltips
 * on hover.
 */
export default function PlotlyChart({ figure, height = 300 }) {
  if (!figure) return null;
  const { data = [], layout = {} } = figure;
  return (
    <Plot
      data={data}
      layout={{
        ...layout,
        autosize: true,
        dragmode: false,          // no drag-to-zoom, drag-to-select, etc.
        clickmode: 'none',        // clicking a bar does nothing
        hovermode: 'closest',     // keep tooltips
        selectdirection: 'any',
      }}
      config={{
        displayModeBar: false,    // hide the little Plotly toolbar
        responsive: true,
        scrollZoom: false,        // no wheel-zoom
        doubleClick: false,       // no double-click-to-reset
        staticPlot: false,        // keep hover tooltips working
        showAxisDragHandles: false,
        showAxisRangeEntryBoxes: false,
      }}
      useResizeHandler
      style={{ width: '100%', height }}
    />
  );
}
