import 'axios';

declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    metadata?: {
      startTime?: number;
      [key: string]: any; // Allow other metadata properties
    };
  }
}