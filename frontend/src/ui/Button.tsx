import React from "react";
import { cn } from "./cn";

export type ButtonVariant = "primary" | "secondary" | "danger" | "ghost";
export type ButtonSize = "sm" | "md";

export default function Button(props: {
  type?: "button" | "submit";
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  className?: string;
  onClick?: () => void;
  children: React.ReactNode;
}) {
  const {
    type = "button",
    variant = "primary",
    size = "md",
    disabled = false,
    className,
    onClick,
    children,
  } = props;

  const base =
    "inline-flex items-center justify-center rounded-md border font-medium transition focus:outline-none focus:ring-2 focus:ring-indigo-400/40 disabled:opacity-50 disabled:cursor-not-allowed";

  const sizeClasses = size === "sm" ? "px-2.5 py-1.5 text-xs" : "px-3 py-2 text-sm";

  const variantClasses =
    variant === "primary"
      ? "border-indigo-400/40 bg-indigo-500 text-slate-50 hover:bg-indigo-400"
      : variant === "secondary"
        ? "border-slate-700 bg-slate-950/30 text-slate-200 hover:border-slate-600 hover:bg-slate-900/60"
        : variant === "danger"
          ? "border-rose-500/40 bg-rose-600 text-slate-50 hover:bg-rose-500"
          : "border-transparent bg-transparent text-slate-200 hover:bg-slate-800/60";

  return (
    <button
      type={type}
      className={cn(base, sizeClasses, variantClasses, className)}
      disabled={disabled}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
