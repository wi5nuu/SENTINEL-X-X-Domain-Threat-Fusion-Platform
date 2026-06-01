import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": "http://sentinel-api:8000",
      "/ws": {
        target: "ws://sentinel-api:8000",
        ws: true,
      },
    },
  },
});
