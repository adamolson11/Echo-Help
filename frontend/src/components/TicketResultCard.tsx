import React, { type ReactNode } from "react";

export type TicketResult = {
  id: string | number;
  title?: string;
  summary?: string;
  source?: string;
  status?: string;
  priority?: string;
  created_at?: string;
  [key: string]: unknown;
};

export type TicketResultCardProps = {
  ticket: TicketResult;
  isActive: boolean;
  isFlashing: boolean;
  onSelect: () => void;
  highlightedTitle: ReactNode;
  statusPill: ReactNode;
  priorityCell: ReactNode;
  createdAtCell: ReactNode;
  feedbackButtons: ReactNode;
  useSemantic: boolean;
};

const TicketResultCard: React.FC<TicketResultCardProps> = ({
  ticket,
  isActive,
  isFlashing,
  onSelect,
  highlightedTitle,
  statusPill,
  priorityCell,
  createdAtCell,
  feedbackButtons,
  useSemantic,
}) => {
  const aiScore = (ticket as any).ai_score as number | undefined;
  const baseRowClasses =
    "border-t border-slate-800 cursor-pointer " +
    (isActive
      ? "bg-slate-800/90 ring-1 ring-indigo-500"
      : "hover:bg-slate-800/80") +
    (isFlashing ? " ring-2 ring-indigo-400 ring-offset-2 ring-offset-slate-900" : "");

  return (
    <tr id={`ticket-row-${ticket.id}`} data-ticket-id={ticket.id} className={baseRowClasses} onClick={onSelect}>
      <td className="px-4 py-2 font-mono text-xs text-slate-400">{ticket.id}</td>
      <td className="px-4 py-2">
        <div className="flex items-center gap-3">
          <div className="flex-1 flex items-center gap-2">
            <div className="flex-1">{highlightedTitle}</div>
            {ticket.source && (
              <div className="flex-shrink-0">
                <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-300">
                  {String(ticket.source).toUpperCase()}
                </span>
              </div>
            )}
          </div>
          {useSemantic && aiScore !== undefined && (
            <div className="flex-shrink-0">
              <span className="inline-flex items-center gap-2 px-2 py-0.5 rounded-full bg-emerald-900/60 text-emerald-200 text-xs font-medium">
                <span className="font-mono text-[11px]">AI</span>
                <span>{aiScore.toFixed(2)}</span>
              </span>
            </div>
          )}
          <div className="flex-shrink-0 ml-2 flex items-center gap-1">{feedbackButtons}</div>
        </div>
      </td>
      <td className="px-4 py-2">{statusPill}</td>
      <td className="px-4 py-2">{priorityCell}</td>
      <td className="px-4 py-2 text-xs text-slate-400">{createdAtCell}</td>
    </tr>
  );
};

export default TicketResultCard;
