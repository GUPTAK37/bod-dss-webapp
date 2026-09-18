import React, { useEffect, useMemo, useRef, useState } from 'react';

const NONE_SENTINEL = '__NONE__';

/**
 * Tableau-style multi-select popover.
 *
 * Value semantics (SQL-facing, passed to backend `_in_clause`):
 *   - `[]`               → (All) — every option, no WHERE clause added
 *   - `['__NONE__']`     → (None) — explicit "match nothing" (produces
 *                          `col IN ('__NONE__')` server-side, which is
 *                          intentionally an empty result set)
 *   - `[a, b]`           → partial — `col IN (a, b)`
 *
 * The (All) checkbox toggles between the first two states. Clicking any
 * individual item transitions to partial (or back to All when every real
 * item is checked, or to None when every real item is unchecked).
 */
export default function MultiSelect({
  id,
  label,
  options,
  value,
  onChange,
  className = '',
  labelClass = 'param-label',
  searchable, // undefined → auto (>10 opts)
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    const onDoc = (e) => {
      if (open && ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  const opts = options || [];
  const total = opts.length;
  const useSearch = searchable == null ? total > 10 : !!searchable;

  // Derive the current visual mode from the value.
  const isAllMode = !value || value.length === 0;
  const isNoneMode = Array.isArray(value)
    && value.length === 1
    && value[0] === NONE_SENTINEL;

  const selectedSet = useMemo(() => {
    if (isAllMode) return new Set(opts);
    if (isNoneMode) return new Set();
    return new Set(value);
  }, [isAllMode, isNoneMode, value, opts]);

  const allChecked = isAllMode;

  const btnText = useMemo(() => {
    if (isAllMode) return '(All)';
    if (isNoneMode || selectedSet.size === 0) return '(None)';
    if (selectedSet.size === total && total > 0) return '(All)';
    if (selectedSet.size === 1) return String([...selectedSet][0]);
    return '(Multiple Values)';
  }, [isAllMode, isNoneMode, selectedSet, total]);

  const filtered = useMemo(() => {
    if (!query.trim()) return opts;
    const q = query.trim().toLowerCase();
    return opts.filter((o) => String(o).toLowerCase().includes(q));
  }, [opts, query]);

  const toggleAll = () => {
    if (allChecked) {
      // Unchecking (All): visually uncheck every real item, and tell the
      // backend to match nothing.
      onChange([NONE_SENTINEL]);
    } else {
      // Checking (All): everything on, no filter applied.
      onChange([]);
    }
  };

  const setOne = (o, checked) => {
    const next = new Set(selectedSet);
    if (checked) next.add(o);
    else next.delete(o);

    if (next.size === total) {
      onChange([]);                       // -> (All)
    } else if (next.size === 0) {
      onChange([NONE_SENTINEL]);          // -> (None)
    } else {
      onChange([...next]);                // -> partial
    }
  };

  return (
    <div className="param-cell" ref={ref}>
      <div className={labelClass}>{label}</div>
      <div className="ms-cell" style={{ position: 'relative' }}>
        <button
          type="button"
          className={`ms-btn ${className}`.trim()}
          onClick={() => setOpen((o) => !o)}
          title={btnText}
        >
          <span className="ms-btn-text">{btnText}</span>
          <span className="ms-btn-arrow">&#9662;</span>
        </button>
        {open && (
          <div className="ms-pop" style={popStyle}>
            <div className="ms-body">
              {useSearch && (
                <input
                  type="search"
                  className="ms-search"
                  placeholder="Search…"
                  autoComplete="off"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              )}
              <div className="ms-chk" style={{ maxHeight: 260, overflow: 'auto' }}>
                <label className="ms-checkbox-label" style={rowStyle}>
                  <input
                    type="checkbox"
                    className="ms-checkbox"
                    checked={allChecked}
                    onChange={toggleAll}
                  />
                  (All)
                </label>
                {filtered.map((o) => (
                  <label key={o} className="ms-checkbox-label" style={rowStyle}>
                    <input
                      type="checkbox"
                      className="ms-checkbox"
                      checked={selectedSet.has(o)}
                      onChange={(e) => setOne(o, e.target.checked)}
                    />
                    {o}
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const popStyle = {
  position: 'absolute',
  top: '100%',
  left: 0,
  zIndex: 50,
  background: '#fff',
  border: '1px solid #B8B8B8',
  boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
  minWidth: 220,
};
const rowStyle = { display: 'block', padding: '2px 4px' };
