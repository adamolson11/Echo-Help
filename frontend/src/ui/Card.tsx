import React from "react";
import { cn } from "./cn";

export default function Card(props: { className?: string; children: React.ReactNode }) {
  return (
    <div className={cn("rounded-xl border border-slate-800 bg-slate-900/40 p-4", props.className)}>
      {props.children}
    </div>
  );
}
