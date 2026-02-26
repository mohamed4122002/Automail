import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        // Legacy variants support
        success: "border-transparent bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20",
        warning: "border-transparent bg-amber-500/10 text-amber-400 hover:bg-amber-500/20",
        error: "border-transparent bg-red-500/10 text-red-400 hover:bg-red-500/20",
        info: "border-transparent bg-sky-500/10 text-sky-400 hover:bg-sky-500/20",
        neutral: "border-transparent bg-slate-700/50 text-slate-400 hover:bg-slate-700/70",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
  VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
  // Try to use the cva variant; if it's a string not in the map, 
  // we can either pass it as a classname or default to outline. 
  // However, `CampaignDetail` is passing things like `bg-blue-500`.
  // The cva won't handle that.

  // Actually, Shadcn's badge accepts `className`. 
  // If `CampaignDetail` passes arbitrary classes in `className`, that's fine.
  // BUT the `variant` prop must match `default|secondary|destructive|outline` 
  // OR be `null`/`undefined`.

  // The existing code was:
  /*
  const colors: any = {
      sent: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      ...
  };
  <Badge variant="outline" className={colors[item.status]}>
  */

  // This means it uses `variant="outline"` (which adds `border`) 
  // and then overrides via `className` with colors.
  // cva's `outline` variant is `text-foreground`.
  // `className` passed to `cn` overrides it.

  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
