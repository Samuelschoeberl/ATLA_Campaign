import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
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
