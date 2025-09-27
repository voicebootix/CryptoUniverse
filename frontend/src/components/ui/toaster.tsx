import { Toaster as SonnerToaster } from 'sonner';

export const Toaster = () => (
  <SonnerToaster
    position="top-right"
    richColors
    expand={false}
    closeButton
    theme="dark"
    toastOptions={{
      duration: 5000,
    }}
  />
);

export default Toaster;
