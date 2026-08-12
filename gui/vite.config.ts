import { defineConfig } from "vite";

// Tauri2 dev convention: fixed port 1420, HMR off (Tauri manages reloads).
export default defineConfig({
  root: ".",
  build: {
    outDir: "dist",
    target: "es2021",
    emptyOutDir: true,
  },
  server: {
    port: 1420,
    strictPort: true,
  },
  clearScreen: false,
});
