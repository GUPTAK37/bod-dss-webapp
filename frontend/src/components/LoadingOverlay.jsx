import React from 'react';

/**
 * Full-page loading overlay shown while Apply Filters is refreshing the
 * cascading filter options + the 10 section queries.
 *
 * `steps` is an ordered list of {label, status} where status is one of
 * 'done' | 'active' | 'pending'.
 */
export default function LoadingOverlay({ visible, title, steps }) {
  if (!visible) return null;
  return (
    <div style={backdropStyle} role="dialog" aria-modal="true" aria-label={title}>
      <div style={cardStyle}>
        <div style={titleStyle}>{title}</div>
        <ul style={listStyle}>
          {steps.map((s, i) => (
            <li key={i} style={itemStyle}>
              <StatusDot status={s.status} />
              <span style={s.status === 'pending' ? textPendingStyle : textDoneStyle}>
                {s.label}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function StatusDot({ status }) {
  if (status === 'done') {
    return (
      <span style={{ ...dotBaseStyle, background: '#2AA198', color: 'white' }}>
        <svg width="10" height="10" viewBox="0 0 12 12" aria-hidden>
          <path d="M2 6 L5 9 L10 3" stroke="white" strokeWidth="2" fill="none"
                strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    );
  }
  if (status === 'active') {
    return <span style={{ ...dotBaseStyle, background: 'transparent' }}>
      <span style={spinnerStyle} />
    </span>;
  }
  return <span style={{ ...dotBaseStyle, background: 'transparent',
                        border: '1.5px solid #CCC' }} />;
}

// ---- styles ---------------------------------------------------------------

const backdropStyle = {
  position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
  background: 'rgba(0, 0, 0, 0.25)', zIndex: 9999,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  fontFamily: '"Trebuchet MS", Trebuchet, Arial, sans-serif',
};

const cardStyle = {
  background: '#FFFFFF',
  padding: '24px 32px',
  minWidth: 320,
  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.15)',
  borderRadius: 2,
};

const titleStyle = {
  fontSize: 15, fontWeight: 700, color: '#222',
  marginBottom: 14,
};

const listStyle = {
  listStyle: 'none', margin: 0, padding: 0,
};

const itemStyle = {
  display: 'flex', alignItems: 'center', gap: 12,
  padding: '6px 0', fontSize: 13,
};

const dotBaseStyle = {
  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
  width: 18, height: 18, borderRadius: '50%',
  border: '1.5px solid transparent',
  flexShrink: 0,
};

const spinnerStyle = {
  display: 'inline-block',
  width: 14, height: 14,
  border: '2px solid #DDD',
  borderTopColor: '#0000C9',
  borderRadius: '50%',
  animation: 'bod-spin 0.8s linear infinite',
};

const textDoneStyle = { color: '#222' };
const textPendingStyle = { color: '#888' };

// Inject the keyframes once.
if (typeof document !== 'undefined' && !document.getElementById('bod-spin-kf')) {
  const style = document.createElement('style');
  style.id = 'bod-spin-kf';
  style.textContent = '@keyframes bod-spin { to { transform: rotate(360deg); } }';
  document.head.appendChild(style);
}
