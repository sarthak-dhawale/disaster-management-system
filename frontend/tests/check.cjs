/* Dependency-free source checks; browser and MySQL checks are documented separately. */
const fs = require('node:fs'),
  path = require('node:path'),
  vm = require('node:vm'),
  assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
let pages = 0,
  scripts = 0;
for (const name of fs.readdirSync(root).filter((n) => n.endsWith('.html'))) {
  const source = fs.readFileSync(path.join(root, name), 'utf8');
  pages++;
  assert(source.includes('name="viewport"'), `${name}: missing responsive viewport`);
  for (const [, asset] of source.matchAll(/(?:src|href)="([^"]+)"/g)) {
    if (asset.startsWith('#') || /^https?:/.test(asset)) continue;
    assert(fs.existsSync(path.join(root, asset)), `${name}: missing ${asset}`);
  }
}
for (const name of fs.readdirSync(path.join(root, 'js')).filter((n) => n.endsWith('.js'))) {
  const source = fs.readFileSync(path.join(root, 'js', name), 'utf8');
  new vm.Script(source, { filename: name });
  scripts++;
  assert(
    !/\b(?:alert|confirm)\s*\(/.test(source),
    `${name}: ordinary interactions must use inline messages/dialogs`,
  );
  assert(
    !/password_hash/.test(source) || name === 'common.js',
    `${name}: password hash UI is not allowed`,
  );
}
const context = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root, 'js/modules.js'), 'utf8'), context);
const moduleNames = vm.runInContext('Object.keys(modules)', context);
for (const name of moduleNames)
  assert(fs.existsSync(path.join(root, name + '.html')), `Missing module page ${name}`);
for (const name of ['audit-history', 'resource-movements', 'analytics'])
  assert(fs.existsSync(path.join(root, name + '.html')));
assert.equal(moduleNames.length, 10);
assert.equal(pages, 18);
console.log(
  `PASS: ${pages} pages, ${scripts} scripts, all local assets and 10 management module links plus 3 history/report pages; JavaScript syntax valid.`,
);
