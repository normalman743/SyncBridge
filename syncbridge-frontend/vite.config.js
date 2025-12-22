/// <reference types="vitest" />
/// <reference types="vite/client" />

import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',   // 关键：使用浏览器环境
    globals: true,          // 允许 describe/it/expect 这些全局函数
    setupFiles: './vitest.setup.js',
  },
});