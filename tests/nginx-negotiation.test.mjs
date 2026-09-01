import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { request } from 'node:http';
import { resolve } from 'node:path';

// Runs the real nginx config from deploy/nginx/ against a fixture site inside Docker.
const REPO = resolve(import.meta.dirname, '..');
const SITE_ROOT = resolve(REPO, 'tests/.site');
const IMAGE = 'nginx:1.18-alpine';

let containerId;
let baseUrl;

function docker(...args) {
  return execFileSync('docker', args, { encoding: 'utf8' }).trim();
}

function writeSite() {
  rmSync(SITE_ROOT, { recursive: true, force: true });
  for (const dir of ['trevoga', 'nomarkdown', 'images']) {
    mkdirSync(resolve(SITE_ROOT, dir), { recursive: true });
  }
  writeFileSync(resolve(SITE_ROOT, 'index.html'), '<html><body>home html</body></html>');
  writeFileSync(resolve(SITE_ROOT, 'index.md'), '# home markdown\n');
  writeFileSync(resolve(SITE_ROOT, 'trevoga/index.html'), '<html><body>trevoga html</body></html>');
  writeFileSync(resolve(SITE_ROOT, 'trevoga/index.md'), '# trevoga markdown\n');
  writeFileSync(resolve(SITE_ROOT, 'nomarkdown/index.html'), '<html><body>no markdown here</body></html>');
  writeFileSync(resolve(SITE_ROOT, '404.html'), '<html><body>404 html</body></html>');
  writeFileSync(resolve(SITE_ROOT, '404.md'), '# 404 markdown\n');
  writeFileSync(resolve(SITE_ROOT, 'robots.txt'), 'User-agent: *\n');
  writeFileSync(resolve(SITE_ROOT, 'images/photo.png'), 'not really a png');
}

function get(path, accept) {
  // node:http adds no Accept of its own, so `accept === null` reproduces a request without the header
  return new Promise((res, rej) => {
    const headers = accept === null ? {} : { Accept: accept };
    const req = request(`${baseUrl}${path}`, { headers }, response => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', chunk => { body += chunk; });
      response.on('end', () => res({ status: response.statusCode, headers: response.headers, body }));
    });
    req.on('error', rej);
    req.end();
  });
}

async function waitForNginx() {
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      await get('/', null);
      return;
    } catch {
      await new Promise(res => setTimeout(res, 200));
    }
  }
  throw new Error(`nginx did not start: ${docker('logs', containerId)}`);
}

before(async () => {
  writeSite();
  containerId = docker(
    'run', '-d', '--rm', '-p', '127.0.0.1:0:80',
    '-v', `${resolve(REPO, 'tests/fixtures/nginx.conf')}:/etc/nginx/nginx.conf:ro`,
    '-v', `${resolve(REPO, 'deploy/nginx/conf.d/markdown-negotiation.conf')}:/etc/nginx/conf.d/markdown-negotiation.conf:ro`,
    '-v', `${resolve(REPO, 'deploy/nginx/snippets/markdown-location.conf')}:/etc/nginx/snippets/markdown-location.conf:ro`,
    '-v', `${SITE_ROOT}:/var/www/site:ro`,
    IMAGE,
  );
  baseUrl = `http://${docker('port', containerId, '80').split('\n')[0]}`;
  await waitForNginx();
});

after(() => {
  if (containerId) docker('rm', '-f', containerId);
  rmSync(SITE_ROOT, { recursive: true, force: true });
});

test('serves markdown for Accept: text/markdown', async () => {
  const response = await get('/trevoga/', 'text/markdown');

  assert.equal(response.status, 200);
  assert.equal(response.headers['content-type'], 'text/markdown; charset=utf-8');
  assert.equal(response.body, '# trevoga markdown\n');
});

test('serves markdown for the site root', async () => {
  const response = await get('/', 'text/markdown');

  assert.equal(response.body, '# home markdown\n');
});

test('markdown responses vary on Accept', async () => {
  const response = await get('/trevoga/', 'text/markdown');

  assert.equal(response.headers.vary, 'Accept, Accept-Encoding');
});

test('html responses vary on Accept', async () => {
  const response = await get('/trevoga/', 'text/html');

  assert.equal(response.headers.vary, 'Accept, Accept-Encoding');
});

test('keeps serving html when the Accept header is empty', async () => {
  const response = await get('/trevoga/', '');

  assert.equal(response.status, 200);
  assert.equal(response.body, '<html><body>trevoga html</body></html>');
});

test('keeps serving html to browsers', async () => {
  const browserAccept = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8';
  const response = await get('/trevoga/', browserAccept);

  assert.equal(response.status, 200);
  assert.match(response.headers['content-type'], /^text\/html/);
  assert.equal(response.body, '<html><body>trevoga html</body></html>');
});

test('keeps serving html when no Accept header is sent', async () => {
  const response = await get('/trevoga/', null);

  assert.equal(response.status, 200);
  assert.equal(response.body, '<html><body>trevoga html</body></html>');
});

test('keeps serving html for a wildcard Accept', async () => {
  const response = await get('/trevoga/', '*/*');

  assert.equal(response.status, 200);
  assert.equal(response.body, '<html><body>trevoga html</body></html>');
});

test('honors q-values when html is preferred', async () => {
  const response = await get('/trevoga/', 'text/html;q=0.9, text/markdown;q=0.8');

  assert.equal(response.status, 200);
  assert.equal(response.body, '<html><body>trevoga html</body></html>');
});

test('honors q-values when markdown is preferred', async () => {
  const response = await get('/trevoga/', 'text/markdown;q=0.9, text/html;q=0.8');

  assert.equal(response.status, 200);
  assert.equal(response.body, '# trevoga markdown\n');
});

test('honors q-values when markdown and html are equally preferred', async () => {
  const response = await get('/trevoga/', 'text/markdown;q=0.5, text/html;q=0.5');

  assert.equal(response.status, 200);
  assert.equal(response.body, '# trevoga markdown\n');
});

test('treats markdown with q=0 as rejected', async () => {
  const response = await get('/trevoga/', 'text/markdown;q=0, text/html');

  assert.equal(response.status, 200);
  assert.equal(response.body, '<html><body>trevoga html</body></html>');
});

test('rejects a page request that accepts neither markdown nor html', async () => {
  const response = await get('/trevoga/', 'application/pdf');

  assert.equal(response.status, 406);
  assert.equal(response.headers.vary, 'Accept, Accept-Encoding');
});

test('never rejects asset requests', async () => {
  const response = await get('/images/photo.png', 'application/pdf');

  assert.equal(response.status, 200);
  assert.equal(response.headers['content-type'], 'image/png');
});

test('falls back to html for a page without a markdown variant', async () => {
  const response = await get('/nomarkdown/', 'text/markdown');

  assert.equal(response.status, 200);
  assert.equal(response.body, '<html><body>no markdown here</body></html>');
});

test('leaves files with their own media type alone', async () => {
  const response = await get('/robots.txt', 'text/markdown');

  assert.equal(response.status, 200);
  assert.match(response.headers['content-type'], /^text\/plain/);
});

test('serves markdown for a page built as a single file', async () => {
  const response = await get('/404', 'text/markdown');

  assert.equal(response.status, 200);
  assert.equal(response.body, '# 404 markdown\n');
});

test('still resolves an extensionless page url', async () => {
  const response = await get('/trevoga', 'text/markdown');

  assert.equal(response.status, 200);
  assert.equal(response.body, '# trevoga markdown\n');
});
