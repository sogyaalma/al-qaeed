// Syntax validation only: browser tests verify actual cascade and token application.
const fs = require('node:fs');
const path = require('node:path');
const postcss = require('postcss');
for (const name of fs.readdirSync('dist/assets/css').filter(n => n.endsWith('.css'))) {
  const file = path.join('dist/assets/css', name);
  const source = fs.readFileSync(file, 'utf8');
  if (source.slice(1).includes('\uFEFF')) throw new Error(`${file}: embedded BOM can break a selector`);
  postcss.parse(source, { from: file });
  console.log(`PASS CSS syntax ${file}`);
}
