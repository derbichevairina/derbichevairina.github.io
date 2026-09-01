import TurndownService from 'turndown';

const STRIPPED_TAGS = ['script', 'style', 'noscript', 'svg', 'iframe'];

const turndown = new TurndownService({
  headingStyle: 'atx',
  bulletListMarker: '-',
  codeBlockStyle: 'fenced',
  emDelimiter: '*',
});

// decorative markup carries no meaning for a reader that only gets the text
turndown.remove(STRIPPED_TAGS);

// images have a built-in rule, which takes precedence over remove(), so drop them explicitly
turndown.addRule('images', { filter: ['img', 'picture'], replacement: () => '' });

function extractMain(html) {
  // the layout wraps page content in a single <main>; everything else is chrome
  const start = html.indexOf('<main');
  const end = html.lastIndexOf('</main>');
  if (start === -1 || end === -1) return null;
  return html.slice(html.indexOf('>', start) + 1, end);
}

function extractCanonical(html) {
  const match = html.match(/<link\s+rel="canonical"\s+href="([^"]+)"/i);
  return match ? match[1] : null;
}

export function htmlToMarkdown(html) {
  // returns null for pages without a <main> block — nothing to serve as markdown
  const main = extractMain(html);
  if (main === null) return null;

  const body = turndown
    .turndown(main)
    .replace(/^(\s*)-\s{3}/gm, '$1- ')
    // list items in the layout start with a decorative em dash in its own span
    .replace(/^(\s*- )—\s+/gm, '$1')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  const canonical = extractCanonical(html);
  const source = canonical ? `\n\nИсточник: ${canonical}\n` : '\n';
  return `${body}${source}`;
}
