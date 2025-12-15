import React from "react";

export default function SectionHeader(props: {
  title: string;
  description?: string;
  right?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-4">
      <div>
        <h2 className="text-lg font-semibold">{props.title}</h2>
        {props.description && <p className="text-sm text-slate-300">{props.description}</p>}
      </div>
      {props.right && <div className="shrink-0">{props.right}</div>}
    </div>
  );
}
