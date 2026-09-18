import React, { useEffect, useMemo, useRef, useState } from 'react';

const NONE_SENTINEL = '__NONE__';

/**
 * Tableau-style multi-select popover with its OWN Apply / Cancel buttons.
 *
 * Behavior:
 *   - Opening the popover snapshots the committed `value` into a local
 *     draft. All checkbox interactions edit the draft only.
 *   - **Apply** commits the draft to the parent (`onChange`), closes the
 *     popover, and triggers a dashboard refresh.
 *   - **Cancel** (or clicking outside) discards the draft and closes.
 *   - No dashboard refetch fires until Apply is clicked.
 *
 * SQL-facing value semantics (unchanged):
 *   - `[]`               → (All)
 *   - `['__NONE__']`     → (None) — match nothing
 *   - `[a, b, ...]`      → partial
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
  const [draft, setDraft] = useState(value || []);
  const ref = useRef(null);

  // Whenever the popover opens, snapshot the currently-committed value.
  useEffect(() => {
    if (open) setDraft(value || []);
  }, [open, value]);

  // Close on outside click (treated as Cancel — draft is discarded).
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

  // Derive draft mode.
  const draftIsAll = !draft || draft.length === 0;
  const draftIsNone = Array.isArray(draft)
    && draft.length === 1
    && draft[0] === NONE_SENTINEL;

  const draftSet = useMemo(() => {
    if (draftIsAll) return new Set(opts);
    if (draftIsNone) return new Set();
    return new Set(draft);
  }, [draftIsAll, draftIsNone, draft, opts]);

  // Committed-value → button text.
  const committedIsAll = !value || value.length === 0;
  const committedIsNone = Array.isArray(value)
    && value.length === 1
    && value[0] === NONE_SENTINEL;

  const btnText = useMemo(() => {
    if (committedIsAll) return '(All)';
    if (committedIsNone) return '(None)';
    if (value.length === 1) return String(value[0]);
    if (value.length === total) return '(All)';
    return '(Multiple Values)';
  }, [committedIsAll, committedIsNone, value, total]);

  const filtered = useMemo(() => {
    if (!query.trim()) return opts;
    const q = query.trim().toLowerCase();
    return opts.filter((o) => String(o).toLowerCase().includes(q));
  }, [opts, query]);

  const toggleAll = () => {
    if (draftIsAll) setDraft([NONE_SENTINEL]);
    else setDraft([]);
  };

  const setOne = (o, checked) => {
    const next = new Set(draftSet);
    if (checked) next.add(o);
    else next.delete(o);
    if (next.size === total) setDraft([]);
    else if (next.size === 0) setDraft([NONE_SENTINEL]);
    else setDraft([...next]);
  };

  const handleApply = () => {
    onChange(draft);
    setOpen(false);
  };

  const handleCancel = () => {
    setDraft(value || []);
    setOpen(false);
  };

  // Enable Apply only when the draft differs from the committed value.
  const dirty = !arraysEqual(draft, value);

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
            <div className="ms-body" style={bodyStyle}>
              {useSearch && (
                <input
                  type="search"
                  className="ms-search"
                  placeholder="Search…"
                  autoComplete="off"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  style={stickyTopStyle}
                />
              )}
              <div className="ms-chk" style={scrollListStyle}>
                <label className="ms-checkbox-label" style={rowStyle}>
                  <input
                    type="checkbox"
                    className="ms-checkbox"
                    checked={draftIsAll}
                    onChange={toggleAll}
                  />
                  (All)
                </label>
                {filtered.map((o) => (
                  <label key={o} className="ms-checkbox-label" style={rowStyle}>
                    <input
                      type="checkbox"
                      className="ms-checkbox"
                      checked={draftSet.has(o)}
                      onChange={(e) => setOne(o, e.target.checked)}
                    />
                    {o}
                  </label>
                ))}
              </div>
              <div style={btnRowStyle}>
                <button type="button"
                        disabled={!dirty}
                        style={{ ...cancelBtnStyle,
                                 ...(dirty ? {} : cancelBtnDisabledStyle) }}
                        onClick={handleCancel}
                        title={dirty
                          ? 'Discard changes'
                          : 'No changes to cancel'}>Cancel</button>
                <button type="button"
                        disabled={!dirty}
                        style={{ ...applyBtnStyle,
                                 ...(dirty ? {} : applyBtnDisabledStyle) }}
                        onClick={handleApply}
                        title={dirty
                          ? 'Apply and refresh'
                          : 'No changes to apply'}>Apply</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function arraysEqual(a, b) {
  const A = a || [];
  const B = b || [];
  if (A.length !== B.length) return false;
  const s = new Set(A);
  for (const x of B) if (!s.has(x)) return false;
  return true;
}

// ---- styles ---------------------------------------------------------------
//
// IMPORTANT: `.ms-body` in tableau_theme.css is the SOLE scroll container
// (max-height: 300px, overflow-y: auto). The search bar stays visible via
// `position: sticky; top: 0` — same trick used here for the Apply/Cancel
// row (`position: sticky; bottom: 0`).
//
// Flex layout on `.ms-pop` doesn't work because the CSS forces
// `.ms-chk { overflow: visible !important }` on all descendants.

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

// No layout overrides — let .ms-body use its own CSS (max-height 300, scroll).
const bodyStyle = undefined;
const stickyTopStyle = undefined;
const scrollListStyle = undefined;

const rowStyle = { display: 'block', padding: '2px 4px' };

const btnRowStyle = {
  // Pin the button row to the bottom of the scroll container.
  position: 'sticky',
  bottom: 0,
  zIndex: 10,
  background: '#FFFFFF',
  display: 'flex',
  gap: 6,
  justifyContent: 'flex-end',
  padding: '6px 4px',
  borderTop: '1px solid #E5E5E5',
  marginTop: 4,
  // Nudge back to line up with the .ms-body padding (4px 6px).
  marginLeft: -6,
  marginRight: -6,
  paddingLeft: 6,
  paddingRight: 6,
};

const applyBtnStyle = {
  background: '#0000C9', color: 'white',
  border: 'none', padding: '4px 12px',
  fontSize: 11, fontWeight: 600,
  cursor: 'pointer', borderRadius: 2,
};
const applyBtnDisabledStyle = {
  background: '#B0B0B0', cursor: 'not-allowed',
};
const cancelBtnStyle = {
  background: '#FFFFFF', color: '#333',
  border: '1px solid #B8B8B8', padding: '4px 12px',
  fontSize: 11, cursor: 'pointer', borderRadius: 2,
};
const cancelBtnDisabledStyle = {
  color: '#B0B0B0', borderColor: '#DDD',
  cursor: 'not-allowed', background: '#F5F5F5',
};
