import React from "react";
import { cn } from "./cn";

export default function TextArea(
  props: React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
    className?: string;
  }
) {
  const { className, ...rest } = props;
  return (
    <textarea
      {...rest}
      className={cn(
        "w-full rounded-md border border-slate-700 bg-slate-950/40 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-indigo-400/50 focus:outline-none focus:ring-2 focus:ring-indigo-400/20",
        className
      )}
    />
  );
}
