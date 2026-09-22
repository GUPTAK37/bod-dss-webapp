import React, { useEffect, useState } from 'react';
import { getRefreshDate } from '../api';
import logoUrl from '../assets/Pfizer_Logo.png';

/**
 * Top header — mirrors the Tableau workbook header:
 *   Left:  Pfizer logo + workbook title
 *   Right: two red date pills (Data Available Until / Data Refresh Date)
 */
export default function AppHeader() {
  const [refresh, setRefresh] = useState('');
  const [available, setAvailable] = useState('');

  useEffect(() => {
    getRefreshDate()
      .then((r) => {
        setRefresh(r.date ? formatDate(r.date) : '');
        setAvailable(r.available_until ? formatDate(r.available_until) : '');
      })
      .catch(() => {});
  }, []);

  return (
    <div className="app-header">
      <div className="app-header-left">
        <img src={logoUrl} alt="Pfizer" className="app-header-logo" />
        <div className="app-title">Covid-19 Quality Care Insights Tool</div>
      </div>
      <div className="app-header-right">
        <div className="app-header-date">
          <span className="app-header-date-label">Data Available Until:</span>
          <span className="app-header-date-value">{available || '—'}</span>
        </div>
        <div className="app-header-date">
          <span className="app-header-date-label">Data Refresh Date:</span>
          <span className="app-header-date-value">{refresh || '—'}</span>
        </div>
      </div>
    </div>
  );
}

// Format 'YYYY-MM-DD' → "14 Aug' 26" (matches the Tableau workbook).
function formatDate(iso) {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const day = String(d.getDate()).padStart(2, '0');
  const mon = d.toLocaleString('en-US', { month: 'short' });
  const yy  = String(d.getFullYear()).slice(-2);
  return `${day} ${mon}' ${yy}`;
}
