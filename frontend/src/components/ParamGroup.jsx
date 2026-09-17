import React from 'react';

export default function ParamGroup({ title, children, flex = 1 }) {
  return (
    <div className="param-group" style={{ flex }}>
      <div className="param-group-title">{title}</div>
      <div className="param-group-body">{children}</div>
    </div>
  );
}
