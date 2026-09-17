import React, { useEffect, useRef, useState } from 'react';

/**
 * Tableau-style single-select popover (mirrors _ss in bod_app/layouts/bod.py).
 *
 * `options` can be:
 *   - array of strings   (value == label)
 *   - array of {value, label}  or object {value: label}
 */
export default function SingleSelect({
  id,
  label,
  options,
  value,
  onChange,
  className = '',
  labelClass = 'param-label',
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    const onDoc = (e) => {
      if (open && ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const opts = normalize(options);
  const current = opts.find((o) => o.value === value);

  return (
    <div className="param-cell" ref={ref}>
      <div className={labelClass}>{label}</div>
      <div className="ms-cell" style={{ position: 'relative' }}>
        <button
          type="button"
          className={`ms-btn ${className}`.trim()}
          onClick={() => setOpen((o) => !o)}
        >
          <span className="ms-btn-text">{current ? current.label : ''}</span>
          <span className="ms-btn-arrow">&#9662;</span>
        </button>
        {open && (
          <div className="ms-pop" style={popStyle}>
            <div className="ms-body">
              {opts.map((o) => (
                <label key={String(o.value)} className="ms-checkbox-label" style={{ display: 'block' }}>
                  <input
                    type="radio"
                    className="ms-checkbox"
                    name={id}
                    checked={value === o.value}
                    onChange={() => {
                      onChange(o.value);
                      setOpen(false);
                    }}
                  />
                  {o.label}
                </label>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function normalize(options) {
  if (!options) return [];
  if (Array.isArray(options)) {
    if (options.length && typeof options[0] === 'object') return options;
    return options.map((o) => ({ value: o, label: o }));
  }
  return Object.entries(options).map(([k, v]) => ({ value: k, label: v }));
}

const popStyle = {
  position: 'absolute',
  top: '100%',
  left: 0,
  zIndex: 50,
  background: '#fff',
  border: '1px solid #B8B8B8',
  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
  minWidth: 180,
};
