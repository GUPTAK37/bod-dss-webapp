import React, { useEffect, useState } from 'react';
import { getRefreshDate } from '../api';

export default function AppHeader() {
  const [refresh, setRefresh] = useState('');
  useEffect(() => {
    getRefreshDate().then((r) => setRefresh(r.date ? `Data Refresh Date: ${r.date}` : ''))
      .catch(() => setRefresh(''));
  }, []);
  return (
    <div className="app-header">
      <div className="app-title">Covid-19 Quality Care Insights Tool</div>
      <div className="header-refresh">{refresh}</div>
    </div>
  );
}
