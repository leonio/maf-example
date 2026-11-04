import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// The UI is a single-page app: adapter-static writes plain files to build/, and the Python server serves them
// (index.html for every path that is not an API route or a real file). During development `pnpm dev` serves the
// UI on :5173 and proxies /api to the Python server on :8000, so both reload independently.
const api = process.env.PIPELINE_API ?? 'http://127.0.0.1:8000';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter: adapter({ fallback: 'index.html' })
		})
	],
	server: {
		proxy: {
			// Server-sent events need the proxy to pass chunks through as they arrive, which Vite does by default.
			'/api': { target: api, changeOrigin: true }
		}
	}
});
