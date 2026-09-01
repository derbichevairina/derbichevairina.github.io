import { readdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { htmlToMarkdown } from './html-to-markdown.mjs';

const DIST = 'dist';

async function* htmlFiles(dir) {
  // walks dist/ and yields every built page (index.html of each route)
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* htmlFiles(path);
    else if (entry.name.endsWith('.html')) yield path;
  }
}

async function main() {
  let written = 0;
  for await (const file of htmlFiles(DIST)) {
    const markdown = htmlToMarkdown(await readFile(file, 'utf8'));
    if (markdown === null) continue;
    await writeFile(file.replace(/\.html$/, '.md'), markdown, 'utf8');
    written += 1;
  }
  console.log(`generated ${written} markdown variants in ${DIST}/`);
}

await main();
