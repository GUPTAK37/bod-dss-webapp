import React, { useEffect, useMemo, useRef, useState } from 'react';

const ALL = '__ALL__';

/**
 * Tableau-style multi-select popover.
 * Ports the (All)-sentinel, "(Multiple Values)" text, and search-filter
 * behavior from the JS clientside callbacks in bod_app/layouts/bod.py.
 *
 * `options`: string[] (the "real" option list — the (All) row is prepended
 *   internally).
 * `value`: string[] — the *SQL-facing* value list. Empty [] means "no filter"
 *   (i.e. (All) is checked).
 * `onChange`: called with the new SQL-facing value list.
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

  // Selected set (SQL-facing = empty means (All)).
  const selectedSet = useMemo(() => {
    if (!value || value.length === 0) return new Set(opts); // (All)
    return new Set(value);
  }, [value, opts]);

  const allChecked = selectedSet.size === total && total > 0;
  const noneChecked = selectedSet.size === 0;

  // Button text.
  const btnText = useMemo(() => {
    if (allChecked || (value && value.length === 0)) return '(All)';
    if (selectedSet.size === 0) return '(None)';
    if (selectedSet.size === 1) return String([...selectedSet][0]);
    return '(Multiple Values)';
  }, [allChecked, selectedSet, value]);

  const filtered = useMemo(() => {
    if (!query.trim()) return opts;
    const q = query.trim().toLowerCase();
    return opts.filter((o) => String(o).toLowerCase().includes(q));
  }, [opts, query]);

  const toggleAll = () => {
    if (allChecked) onChange([]);        // sql-facing [] == treat-as-all here == None visually
    else onChange([]);                   // Same: SQL-facing (All) is []
  };

  const setOne = (o, checked) => {
    const next = new Set(selectedSet);
    if (checked) next.add(o);
    else next.delete(o);
    // Collapse to (All) when every real option is checked.
    if (next.size === total) onChange([]);
    else onChange([...next]);
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
                    checked={allChecked || (value && value.length === 0)}
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
