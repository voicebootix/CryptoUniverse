import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

// Production configuration for Render static site deployment
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false, // Disable in production for security
    minify: 'terser',
    target: 'es2020',
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu', '@radix-ui/react-tabs'],
          charts: ['recharts'],
          utils: ['axios', 'zustand', '@tanstack/react-query'],
          animations: ['framer-motion'],
        },
        // Optimize chunk names for caching
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
    // Optimize for production
    cssCodeSplit: true,
    assetsInlineLimit: 4096,
    reportCompressedSize: false,
  },
  define: {
    'process.env.NODE_ENV': JSON.stringify('production'),
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL),
    __DEV__: false,
  },
  // Production server config (for preview)
  preview: {
    port: 3000,
    host: '0.0.0.0',
    strictPort: true,
  },
  // Optimize dependencies
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'axios',
      'zustand',
      '@tanstack/react-query',
      'recharts',
      'framer-motion',
    ],
  },
})
