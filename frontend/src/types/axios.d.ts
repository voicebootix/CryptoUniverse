import 'axios';

declare module 'axios' {
  // Shared metadata interface
  interface Metadata {
    startTime?: number;
    [key: string]: unknown; // Use unknown for type safety
  }

  // Augment both config types
  export interface AxiosRequestConfig {
    metadata?: Metadata;
  }

  export interface InternalAxiosRequestConfig {
    metadata?: Metadata;
  }
}