import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    esbuildOptions: {
      sourcemap: false, // Suppress dep source maps that trigger browser warnings
    },
  },
  build: {
    sourcemap: false, // Disable source maps to prevent warning noise
  },
  server: {
    host: true, // Allow external connections
    allowedHosts: [".trycloudflare.com"], // Allow all Cloudflare tunnel subdomains
    proxy: {
      "/api": {
        target: "http://localhost:9002",
        changeOrigin: true,
      },
      "/player_root": {
        target: "http://localhost:9002",
        changeOrigin: true,
      },
    },
  },
});
