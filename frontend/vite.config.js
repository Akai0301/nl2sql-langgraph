import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { fileURLToPath, URL } from 'node:url';
export default defineConfig({
    plugins: [vue()],
    resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
        },
    },
    server: {
        host: true, // Listen on all addresses
        port: 3000,
        strictPort: false,
        proxy: {
            '/query': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/stream': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/graph': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            '/history': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: '../static',
        emptyOutDir: true,
    },
});
