import test from 'node:test';
import assert from 'node:assert/strict';
import { htmlToMarkdown } from '../scripts/html-to-markdown.mjs';

function page(main) {
  return `<!doctype html><html><head><title>T</title>
    <link rel="canonical" href="https://psyholog-irina.ru/trevoga/" />
    </head><body><header><nav><a href="/">Главная</a></nav></header>
    <main class="flex-1">${main}</main><footer>подвал</footer></body></html>`;
}

test('converts the main block and drops the page chrome', () => {
  const markdown = htmlToMarkdown(page('<h1>Тревога</h1><p>Текст статьи.</p>'));

  assert.match(markdown, /^# Тревога\n\nТекст статьи\./);
  assert.doesNotMatch(markdown, /подвал/);
});

test('appends the canonical url as the source', () => {
  const markdown = htmlToMarkdown(page('<p>Текст.</p>'));

  assert.match(markdown, /\n\nИсточник: https:\/\/psyholog-irina\.ru\/trevoga\/\n$/);
});

test('drops decorative markup', () => {
  const main = '<p>Текст.</p><svg><path d="M0"/></svg><script>alert(1)</script><img src="/a.png" alt="фото">';
  const markdown = htmlToMarkdown(page(main));

  assert.equal(markdown.split('Источник')[0].trim(), 'Текст.');
});

test('cleans up the decorative dash in list items', () => {
  const main = '<ul><li class="flex gap-2"><span>—</span> Учащённое сердцебиение</li></ul>';
  const markdown = htmlToMarkdown(page(main));

  assert.match(markdown, /^- Учащённое сердцебиение$/m);
});

test('keeps links', () => {
  const markdown = htmlToMarkdown(page('<p>Пишите в <a href="https://t.me/derbichevairina">Telegram</a>.</p>'));

  assert.match(markdown, /\[Telegram\]\(https:\/\/t\.me\/derbichevairina\)/);
});

test('returns null for a document without a main block', () => {
  assert.equal(htmlToMarkdown('<html><body><p>Текст.</p></body></html>'), null);
});
