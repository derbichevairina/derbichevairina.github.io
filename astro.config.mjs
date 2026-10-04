import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://psyholog-irina.ru',
  integrations: [sitemap({ filter: (page) => !page.includes('/index2') })],
  vite: {
    plugins: [tailwindcss()],
  },
});
