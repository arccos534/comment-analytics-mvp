import * as React from "react";

import { cn } from "@/lib/utils";

export function Select({ className, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "flex h-11 w-full rounded-xl border border-border bg-white px-3 py-2 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-primary",
        className
      )}
      {...props}
    />
  );
}
