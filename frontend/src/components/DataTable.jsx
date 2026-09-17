import React from 'react';

/**
 * Renders the two table specs produced by backend/renderers.py:
 *   - {type: "matrix", columns, rows, first_col_highlight}
 *   - {type: "grouped_matrix", groups, subcols, rows, first_group_highlight}
 *   - {type: "empty"} — "No data." placeholder.
 * Class names match bod_app/assets/tableau_theme.css for pixel parity.
 */
export default function DataTable({ table }) {
  if (!table || table.type === 'empty') {
    return <div className="empty-note">No data.</div>;
  }
  if (table.type === 'matrix') return <MatrixTable table={table} />;
  if (table.type === 'grouped_matrix') return <GroupedMatrixTable table={table} />;
  return null;
}

function MatrixTable({ table }) {
  const { columns, rows, first_col_highlight } = table;
  return (
    <table>
      <thead>
        <tr>
          <th className="row-label"></th>
          {columns.map((c, i) => (
            <th key={i} className={`num${first_col_highlight && i === 0 ? ' reference-col-header' : ''}`}>
              {c}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, ri) => (
          <tr key={ri}>
            <td className="row-label">{r.label}</td>
            {r.values.map((v, i) => (
              <td key={i} className={`num${first_col_highlight && i === 0 ? ' reference-col-cell' : ''}`}>
                {v}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function GroupedMatrixTable({ table }) {
  const { groups, subcols, rows, first_group_highlight } = table;
  const nSub = subcols.length;
  const groupCls = (gi, base) => base + (first_group_highlight && gi === 0 ? ' reference-col-header' : '');
  const subCls = (gi) => 'num sub-header' + (first_group_highlight && gi === 0 ? ' reference-col-header' : '');
  const cellCls = (gi) => 'num' + (first_group_highlight && gi === 0 ? ' reference-col-cell' : '');
  return (
    <table>
      <thead>
        <tr>
          <th className="row-label" rowSpan={2}></th>
          {groups.map((g, gi) => (
            <th key={gi} className={groupCls(gi, 'num group-header')} colSpan={nSub}>
              {g}
            </th>
          ))}
        </tr>
        <tr>
          {groups.map((_, gi) => (
            <React.Fragment key={gi}>
              {subcols.map((c, ci) => (
                <th key={`${gi}-${ci}`} className={subCls(gi)}>{c}</th>
              ))}
            </React.Fragment>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, ri) => (
          <tr key={ri}>
            <td className="row-label">{r.label}</td>
            {r.values.map((v, i) => {
              const gi = Math.floor(i / nSub);
              return <td key={i} className={cellCls(gi)}>{v}</td>;
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
