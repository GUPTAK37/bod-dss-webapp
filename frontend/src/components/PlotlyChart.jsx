import React from 'react';
import Plot from 'react-plotly.js';

/**
 * Wraps react-plotly.js so a section can pass the raw JSON returned by
 * `fig.to_plotly_json()` on the backend.
 */
export default function PlotlyChart({ figure, height = 300 }) {
  if (!figure) return null;
  const { data = [], layout = {} } = figure;
  return (
    <Plot
      data={data}
      layout={{ ...layout, autosize: true }}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: '100%', height }}
    />
  );
}
