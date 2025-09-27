import { useCallback } from 'react';
import { toast as sonnerToast } from 'sonner';

export type ToastVariant = 'default' | 'destructive';

export interface ToastOptions {
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
}

export const useToast = () => {
  const toast = useCallback(
    ({ title, description, variant = 'default', duration = 5000 }: ToastOptions) => {
      const options = { description, duration } as const;

      if (variant === 'destructive') {
        return sonnerToast.error(title, options);
      }

      return sonnerToast(title, options);
    },
    []
  );

  const dismiss = useCallback((toastId?: string | number) => {
    if (toastId !== undefined) {
      sonnerToast.dismiss(toastId);
    }
  }, []);

  return { toast, dismiss };
};
