import React from 'react'

// Placeholder checkbox component - replace with actual implementation
export interface CheckboxProps {
  id?: string
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
  disabled?: boolean
  className?: string
  children?: React.ReactNode
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ id, checked, onCheckedChange, disabled, className, children, ...props }, ref) => {
    return (
      <label className={`flex items-center space-x-2 ${className || ''}`}>
        <input
          ref={ref}
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onCheckedChange?.(e.target.checked)}
          disabled={disabled}
          className="rounded border border-gray-300"
          {...props}
        />
        {children && <span>{children}</span>}
      </label>
    )
  }
)

Checkbox.displayName = 'Checkbox'