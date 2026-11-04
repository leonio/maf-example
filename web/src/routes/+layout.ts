// A single-page app: everything renders in the browser and talks to the Python API. There is nothing to render on
// a server (the data is live and per run), so SSR and prerendering are off and adapter-static's fallback page boots
// the router for every URL.
export const ssr = false;
export const prerender = false;
