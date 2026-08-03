import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// GitHub Pages serves the repo at /artamatch/, so assets must be requested from there. A local
// `vite dev` / `vite preview` serves from the same base, which keeps the two identical — a base
// that differs between preview and production is the classic way a Pages deploy 404s its own JS.
export default defineConfig({
  base: process.env.AM_BASE ?? "/artamatch/",
  plugins: [react()],
  build: { outDir: "dist", sourcemap: true },
  test: { environment: "node", include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"] },
});
