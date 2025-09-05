import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
  label?: string;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading = false, label, children, disabled, onClick, onKeyDown, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    const isNativeButton = Comp === "button";
    const isDisabled = disabled || loading;
    
    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (isDisabled) return;
      if (onKeyDown) onKeyDown(e);
      if ((e.key === 'Enter' || e.key === ' ') && !e.defaultPrevented) {
        e.preventDefault();
        e.currentTarget.click();
      }
    };

    const handleClick = (e: React.MouseEvent) => {
      if (isDisabled) return;
      onClick?.(e);
    };
    
    return (
      <Comp
        {...props}
        className={cn(
          buttonVariants({ variant, size, className }),
          isDisabled && "pointer-events-none opacity-50"
        )}
        ref={ref}
        type={isNativeButton ? "button" : undefined}
        disabled={isNativeButton ? isDisabled : undefined}
        aria-label={label}
        aria-disabled={isDisabled}
        aria-busy={loading}
        role={!isNativeButton ? "button" : undefined}
        tabIndex={!isNativeButton ? (isDisabled ? -1 : 0) : undefined}
        onClick={!isNativeButton ? handleClick : onClick}
        onKeyDown={!isNativeButton ? handleKeyDown : onKeyDown}
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            <span>Loading...</span>
          </>
        ) : (
          children
        )}
      </Comp>
    );
  }
);

Button.displayName = "Button";

export { Button, buttonVariants };