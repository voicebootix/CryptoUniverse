import React from 'react';

// Simple Dialog replacement components
export interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

export const Dialog: React.FC<DialogProps> = ({ open, onOpenChange, children }) => {
  if (!open) return null;
  
  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={() => onOpenChange(false)}
    >
      {children}
    </div>
  );
};

export const DialogContent: React.FC<{ children: React.ReactNode; className?: string }> = ({ 
  children, 
  className = "" 
}) => (
  <div 
    className={`bg-white rounded-lg p-6 max-w-md w-full mx-4 ${className}`}
    onClick={(e) => e.stopPropagation()}
  >
    {children}
  </div>
);

export const DialogHeader: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="mb-4">{children}</div>
);

export const DialogTitle: React.FC<{ children: React.ReactNode; className?: string }> = ({ 
  children, 
  className = "" 
}) => (
  <h2 className={`text-xl font-semibold ${className}`}>{children}</h2>
);

export const DialogDescription: React.FC<{ children: React.ReactNode; className?: string }> = ({ 
  children, 
  className = "" 
}) => (
  <p className={`text-muted-foreground ${className}`}>{children}</p>
);

export const DialogFooter: React.FC<{ children: React.ReactNode; className?: string }> = ({ 
  children, 
  className = "" 
}) => (
  <div className={`flex gap-2 justify-end mt-4 ${className}`}>{children}</div>
);