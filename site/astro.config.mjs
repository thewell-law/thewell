import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

// Note: @astrojs/sitemap is installed but not activated here. It crashes
// on astro:build:done when there are zero static routes (the case until
// Stage 3 adds the judge pages). Re-add `sitemap()` to the integrations
// array in the PR that introduces real routes.

export default defineConfig({
  site: 'https://thewell.law',
  output: 'static',
  trailingSlash: 'always',
  build: {
    format: 'directory',
  },
  integrations: [
    tailwind({ applyBaseStyles: false }),
  ],
  vite: {
    ssr: {
      // pagefind is loaded at runtime from the built /pagefind/ assets
      noExternal: [],
    },
  },
});
