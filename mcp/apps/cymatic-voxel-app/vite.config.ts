import path from "node:path";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const input = process.env.INPUT ?? "mcp-app.html";

export default defineConfig({
  plugins: [viteSingleFile()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(process.cwd(), input),
    },
  },
});
