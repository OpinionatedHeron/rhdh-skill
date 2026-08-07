#!/usr/bin/env node
/*
  RHDH Yarn bump orchestrator.

  Workspaces: `yarn set version <to>` (+ lock refresh). That owns packageManager,
  yarnPath, and .yarn/releases — do not reimplement those.

  Extras Yarn cannot see: Containerfile / Dockerfile / ENV YARN / embedded
  `yarn set version`, orphan release binaries (distgit), Fullsend helpers,
  and yarn.lock under workspaces that only inherit a root pin.
*/

'use strict';

const fs = require('node:fs');
const path = require('node:path');
const https = require('node:https');
const http = require('node:http');
const os = require('node:os');
const { spawnSync } = require('node:child_process');

const DEFAULT_FROM = ['4.12.0', '4.14.1'];
const CACHE_DIR = path.join(os.homedir(), '.cache', 'rhdh-bump-yarn');

function usage(code = 0) {
  console.log(`Usage:
  bump-yarn.js --to VERSION [--from V1,V2] --root PATH [--root PATH ...]
  bump-yarn.js --scan --root PATH
  bump-yarn.js --to VERSION --root PATH [--dry-run] [--no-refresh-locks]

Defaults: --from ${DEFAULT_FROM.join(',')}
Strategy: yarn set version <to> for matching packageManager dirs; rewrite
Containerfile/Fullsend/orphan binaries; refresh inherited yarn.lock dirs.
`);
  process.exit(code);
}

function parseArgs(argv) {
  const args = {
    from: [...DEFAULT_FROM],
    roots: [],
    to: null,
    scan: false,
    dryRun: false,
    refreshLocks: true,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '-h' || a === '--help') usage(0);
    else if (a === '--scan') args.scan = true;
    else if (a === '--dry-run') args.dryRun = true;
    else if (a === '--no-refresh-locks') args.refreshLocks = false;
    else if (a === '--refresh-locks') args.refreshLocks = true;
    else if (a === '--to') args.to = argv[++i];
    else if (a === '--from') {
      args.from = String(argv[++i] || '')
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
    } else if (a === '--root') args.roots.push(path.resolve(argv[++i]));
    else {
      console.error(`Unknown arg: ${a}`);
      usage(1);
    }
  }
  return args;
}

function esc(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function skipDir(name) {
  return (
    name === '.git' ||
    name === 'node_modules' ||
    name === '.yarn' ||
    name === 'dist' ||
    name === 'coverage' ||
    name === '.turbo'
  );
}

function walk(root, onFile) {
  const stack = [root];
  while (stack.length) {
    const dir = stack.pop();
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const ent of entries) {
      const full = path.join(dir, ent.name);
      if (ent.isDirectory()) {
        if (skipDir(ent.name)) {
          if (ent.name === '.yarn') {
            const releases = path.join(full, 'releases');
            if (fs.existsSync(releases)) stack.push(releases);
          }
          continue;
        }
        stack.push(full);
      } else if (ent.isFile()) onFile(full, ent.name);
    }
  }
}

function readPm(dir) {
  try {
    const pm = JSON.parse(fs.readFileSync(path.join(dir, 'package.json'), 'utf8')).packageManager;
    const m = typeof pm === 'string' && /^yarn@([0-9]+\.[0-9]+\.[0-9]+)/.exec(pm);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

function readYarnPath(dir) {
  try {
    const text = fs.readFileSync(path.join(dir, '.yarnrc.yml'), 'utf8');
    const m = /(?:^|\n)yarnPath:\s*.*yarn-([0-9]+\.[0-9]+\.[0-9]+)\.cjs/.exec(text);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

function explicitPin(dir) {
  return readPm(dir) || readYarnPath(dir);
}

function isFullsend(full, basename) {
  return (
    basename === 'yarn' &&
    full.split(path.sep).join('/').includes('/.fullsend/') &&
    full.endsWith(`${path.sep}bin${path.sep}yarn`)
  );
}

function isExtraText(full, basename) {
  if (basename === 'package.json' || basename === '.yarnrc.yml') return false;
  if (basename === 'Containerfile' || basename === 'Dockerfile' || basename === 'run-e2e.sh') {
    return true;
  }
  if (basename.endsWith('.Containerfile') || basename.endsWith('.Dockerfile')) return true;
  if (basename.endsWith('.sh') && /e2e|yarn|packageManager/i.test(basename + full)) return true;
  return isFullsend(full, basename);
}

function localYarnBin(dir) {
  const releases = path.join(dir, '.yarn', 'releases');
  try {
    const bins = fs
      .readdirSync(releases)
      .filter((n) => /^yarn-[0-9]+\.[0-9]+\.[0-9]+\.cjs$/.test(n))
      .sort();
    return bins.length ? path.join(releases, bins[bins.length - 1]) : null;
  } catch {
    return null;
  }
}

function chmodX(p) {
  try {
    fs.chmodSync(p, 0o755);
  } catch (err) {
    console.error(`warn: chmod +x failed for ${p}: ${err.message}`);
  }
}

function download(url, dest) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https:') ? https : http;
    client
      .get(url, { headers: { 'User-Agent': 'rhdh-bump-yarn' } }, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume();
          download(res.headers.location, dest).then(resolve, reject);
          return;
        }
        if (res.statusCode !== 200) {
          reject(new Error(`GET ${url} → ${res.statusCode}`));
          res.resume();
          return;
        }
        const tmp = `${dest}.partial`;
        const out = fs.createWriteStream(tmp);
        res.pipe(out);
        out.on('finish', () => out.close(() => {
          fs.renameSync(tmp, dest);
          resolve(dest);
        }));
        out.on('error', reject);
      })
      .on('error', reject);
  });
}

/** Only for orphan distgit binaries when no workspace produced yarn-<to>.cjs. */
async function cachedBinary(version) {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  const dest = path.join(CACHE_DIR, `yarn-${version}.cjs`);
  const ok = () => {
    const v = spawnSync(process.execPath, [dest, '-v'], { encoding: 'utf8' });
    return v.status === 0 && String(v.stdout).trim() === version;
  };
  if (fs.existsSync(dest) && ok()) {
    chmodX(dest);
    return dest;
  }
  const tag = encodeURIComponent(`@yarnpkg/cli/${version}`);
  const url = `https://raw.githubusercontent.com/yarnpkg/berry/${tag}/packages/yarnpkg-cli/bin/yarn.js`;
  console.log(`fetch (orphan fallback): ${url}`);
  await download(url, dest);
  chmodX(dest);
  if (!ok()) throw new Error(`cached yarn binary mismatch for ${version}`);
  return dest;
}

function findToBin(root, to) {
  let found = null;
  walk(root, (full, basename) => {
    if (!found && basename === `yarn-${to}.cjs` && full.includes(`${path.sep}.yarn${path.sep}releases${path.sep}`)) {
      found = full;
    }
  });
  return found;
}

function bumpExtraText(content, fromVersions, to) {
  const alt = fromVersions.map(esc).join('|');
  return content
    .replace(new RegExp(`yarn-(?:${alt})\\.cjs`, 'g'), `yarn-${to}.cjs`)
    .replace(new RegExp(`yarn set version (?:${alt})\\b`, 'g'), `yarn set version ${to}`)
    .replace(
      new RegExp(`"packageManager":\\s*"yarn@(?:${alt})(?:\\+[^"]+)?"`, 'g'),
      `"packageManager": "yarn@${to}"`,
    );
}

function skipLock(p) {
  const parts = p.split(path.sep);
  return parts.includes('node_modules') || parts.includes('dist-dynamic') || parts.includes('.git');
}

function lockDirs(root, { from, to }) {
  const fromSet = new Set(from);
  const dirs = [];
  const skipped = [];
  walk(root, (full, basename) => {
    if (basename !== 'yarn.lock' || skipLock(full)) return;
    const dir = path.dirname(full);
    const pin = explicitPin(dir);
    if (pin && pin !== to && !fromSet.has(pin)) skipped.push({ dir, pin });
    else dirs.push(dir);
  });
  return { dirs: dirs.sort(), skipped };
}

function resolveBin(dir, fallback, to) {
  let cur = dir;
  for (let i = 0; i < 8; i += 1) {
    const c = path.join(cur, '.yarn', 'releases', `yarn-${to}.cjs`);
    if (fs.existsSync(c)) return c;
    const parent = path.dirname(cur);
    if (parent === cur) break;
    cur = parent;
  }
  return fallback;
}

function runSetVersion(dir, to, dryRun) {
  const local = localYarnBin(dir);
  if (dryRun) {
    console.log(
      `dry-run: ${dir}: ${local ? `node ${path.relative(dir, local)}` : 'yarn'} set version ${to}`,
    );
    return { status: 0 };
  }
  console.log(`yarn set version: ${dir}`);
  const r = local
    ? spawnSync(process.execPath, [local, 'set', 'version', to], {
      cwd: dir,
      encoding: 'utf8',
      env: { ...process.env, YARN_ENABLE_IMMUTABLE_INSTALLS: 'false' },
      stdio: ['ignore', 'pipe', 'pipe'],
    })
    : spawnSync('yarn', ['set', 'version', to], {
      cwd: dir,
      encoding: 'utf8',
      env: { ...process.env, YARN_ENABLE_IMMUTABLE_INSTALLS: 'false' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
  if (r.status !== 0) {
    console.error(
      `warn: yarn set version failed in ${dir} (exit ${r.status})\n` +
        (r.stderr || r.stdout || '').trim().split('\n').slice(-8).join('\n'),
    );
  }
  const bin = path.join(dir, '.yarn', 'releases', `yarn-${to}.cjs`);
  if (fs.existsSync(bin)) chmodX(bin);
  return r;
}

function scanRoot(root) {
  const releases = [];
  const packageManagers = [];
  const extraPins = [];
  walk(root, (full, basename) => {
    const m = /^yarn-([0-9]+\.[0-9]+\.[0-9]+)\.cjs$/.exec(basename);
    if (m && full.includes(`${path.sep}.yarn${path.sep}releases${path.sep}`)) {
      releases.push({ path: full, version: m[1] });
      return;
    }
    if (basename === 'package.json') {
      const ver = readPm(path.dirname(full));
      if (ver) packageManagers.push({ path: full, version: ver });
      return;
    }
    if (!isExtraText(full, basename)) return;
    let text;
    try {
      text = fs.readFileSync(full, 'utf8');
    } catch {
      return;
    }
    if (text.length > 2_000_000) return;
    const found = new Set();
    for (const re of [/yarn-([0-9]+\.[0-9]+\.[0-9]+)\.cjs/g, /yarn set version ([0-9]+\.[0-9]+\.[0-9]+)/g]) {
      let match;
      while ((match = re.exec(text))) found.add(match[1]);
    }
    if (found.size) extraPins.push({ path: full, versions: [...found].sort() });
  });
  return { releases, packageManagers, extraPins };
}

function printScan(root) {
  const { releases, packageManagers, extraPins } = scanRoot(root);
  const count = (items, key) => {
    const m = new Map();
    for (const it of items) {
      const vs = key ? it[key] : it.versions;
      for (const v of Array.isArray(vs) ? vs : [vs]) m.set(v, (m.get(v) || 0) + 1);
    }
    return m;
  };
  console.log(`\n=== scan ${root} ===`);
  console.log('releases:');
  for (const [v, n] of [...count(releases, 'version')].sort()) console.log(`  yarn-${v}.cjs × ${n}`);
  if (!releases.length) console.log('  (none)');
  console.log('packageManager (yarn set version targets):');
  for (const [v, n] of [...count(packageManagers, 'version')].sort()) console.log(`  yarn@${v} × ${n}`);
  if (!packageManagers.length) console.log('  (none)');
  console.log('extra pins (Containerfile / Fullsend / scripts):');
  for (const [v, n] of [...count(extraPins)].sort()) console.log(`  ${v} × ${n} files`);
  if (!extraPins.length) console.log('  (none)');
}

async function bumpRoot(root, { from, to, dryRun, refreshLocks }) {
  const fromSet = new Set(from);
  const summary = {
    setVersionDirs: [],
    setVersionFailed: [],
    orphanBinaries: [],
    extraFiles: [],
    lockRefresh: [],
    lockRefreshSkipped: [],
    remaining: [],
  };

  const pmDirs = [];
  walk(root, (full, basename) => {
    if (basename !== 'package.json') return;
    const dir = path.dirname(full);
    const ver = readPm(dir);
    if (ver && fromSet.has(ver)) pmDirs.push(dir);
  });
  pmDirs.sort();

  const covered = new Set(pmDirs.map((d) => path.resolve(d)));
  const orphans = [];
  walk(root, (full, basename) => {
    const m = /^yarn-([0-9]+\.[0-9]+\.[0-9]+)\.cjs$/.exec(basename);
    if (!m || !fromSet.has(m[1])) return;
    if (!full.includes(`${path.sep}.yarn${path.sep}releases${path.sep}`)) return;
    const projectDir = path.dirname(path.dirname(path.dirname(full)));
    if (!covered.has(path.resolve(projectDir))) {
      orphans.push({ path: full, dir: projectDir });
    }
  });

  for (const dir of pmDirs) {
    summary.setVersionDirs.push(dir);
    const r = runSetVersion(dir, to, dryRun);
    if (!dryRun && r.status !== 0) summary.setVersionFailed.push(dir);
  }

  let fallback = null;
  if (orphans.length) {
    if (!dryRun) fallback = findToBin(root, to) || (await cachedBinary(to));
    for (const o of orphans) {
      const dest = path.join(path.dirname(o.path), `yarn-${to}.cjs`);
      summary.orphanBinaries.push({ from: o.path, to: dest });
      if (dryRun) {
        console.log(`dry-run: orphan binary ${o.path} → ${dest}`);
        continue;
      }
      fs.copyFileSync(fallback, dest);
      chmodX(dest);
      if (path.resolve(o.path) !== path.resolve(dest)) fs.unlinkSync(o.path);
    }
  }

  walk(root, (full, basename) => {
    if (!isExtraText(full, basename)) return;
    let text;
    try {
      text = fs.readFileSync(full, 'utf8');
    } catch {
      return;
    }
    if (text.length > 2_000_000) return;
    const next = bumpExtraText(text, from, to);
    if (next === text) return;
    summary.extraFiles.push(full);
    if (isFullsend(full, basename) && /yarn-[0-9]+\.[0-9]+\.[0-9]+\.cjs/.test(next)) {
      console.warn(
        `warn: ${full} still hardcodes yarn-*.cjs; prefer yarnPath derivation (rhdh-plugins#4199)`,
      );
    }
    if (dryRun) console.log(`dry-run: extra pin ${path.relative(root, full)}`);
    else fs.writeFileSync(full, next);
  });

  if (!dryRun) {
    const after = scanRoot(root);
    for (const r of after.releases) {
      if (fromSet.has(r.version)) summary.remaining.push(`release ${r.version}: ${r.path}`);
    }
    for (const p of after.packageManagers) {
      if (fromSet.has(p.version)) summary.remaining.push(`packageManager ${p.version}: ${p.path}`);
    }
    for (const p of after.extraPins) {
      const left = p.versions.filter((v) => fromSet.has(v));
      if (left.length) summary.remaining.push(`${left.join(',')}: ${p.path}`);
    }
  }

  if (refreshLocks && !dryRun) {
    if (!fallback) fallback = findToBin(root, to) || (await cachedBinary(to));
    const { dirs, skipped } = lockDirs(root, { from, to });
    summary.lockRefreshSkipped = skipped;
    for (const s of skipped) console.log(`refresh-locks: skip ${s.dir} (explicit pin ${s.pin})`);
    for (const dir of dirs) {
      const yarnBin = resolveBin(dir, fallback, to);
      console.log(`refresh-locks: ${dir}`);
      const r = spawnSync(process.execPath, [yarnBin, 'install', '--mode=update-lockfile'], {
        cwd: dir,
        encoding: 'utf8',
        env: { ...process.env, YARN_ENABLE_IMMUTABLE_INSTALLS: 'false' },
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      const rcPath = path.join(dir, '.yarnrc.yml');
      if (fs.existsSync(rcPath)) {
        const tracked = spawnSync('git', ['ls-files', '--error-unmatch', rcPath], {
          cwd: root,
          encoding: 'utf8',
        });
        if (tracked.status !== 0) {
          try {
            fs.unlinkSync(rcPath);
            console.log(`refresh-locks: removed untracked ${rcPath}`);
          } catch {
            // ignore
          }
        }
      }
      summary.lockRefresh.push({ dir, status: r.status });
      if (r.status !== 0) console.error(`warn: yarn install failed in ${dir} (exit ${r.status})`);
    }
  }

  return summary;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.roots.length) {
    console.error('Provide at least one --root PATH');
    usage(1);
  }
  for (const root of args.roots) {
    if (!fs.existsSync(root)) {
      console.error(`Missing root: ${root}`);
      process.exit(1);
    }
  }
  if (args.scan) {
    for (const root of args.roots) printScan(root);
    return;
  }
  if (!args.to) {
    console.error('--to VERSION is required (unless --scan)');
    usage(1);
  }
  if (!args.from.length) {
    console.error('--from must list at least one version');
    usage(1);
  }

  console.log(`to: ${args.to}`);
  console.log(`from: ${args.from.join(', ')}`);
  console.log(`dry-run: ${args.dryRun}`);
  console.log(`refresh-locks: ${args.refreshLocks}`);
  console.log('strategy: yarn set version + extra pin rewrite');

  let failed = false;
  for (const root of args.roots) {
    const s = await bumpRoot(root, {
      from: args.from,
      to: args.to,
      dryRun: args.dryRun,
      refreshLocks: args.refreshLocks,
    });
    console.log(`\n=== ${args.dryRun ? 'dry-run ' : ''}bump ${root} ===`);
    console.log(`yarn set version dirs: ${s.setVersionDirs.length}`);
    for (const d of s.setVersionDirs.slice(0, 40)) console.log(`  ${path.relative(root, d) || '.'}`);
    if (s.setVersionDirs.length > 40) console.log(`  … +${s.setVersionDirs.length - 40} more`);
    if (s.setVersionFailed.length) {
      failed = true;
      console.log(`yarn set version failed: ${s.setVersionFailed.length}`);
    }
    console.log(`orphan binaries: ${s.orphanBinaries.length}`);
    for (const b of s.orphanBinaries) console.log(`  ${b.from} → ${b.to}`);
    const extras = s.extraFiles.map((f) => path.relative(root, f)).sort();
    console.log(`extra pin files: ${extras.length}`);
    for (const f of extras) console.log(`  ${f}`);
    if (s.remaining.length) {
      failed = true;
      console.log('REMAINING from-versions (unexpected):');
      for (const line of s.remaining) console.log(`  ${line}`);
    } else if (!args.dryRun) console.log('remaining from-versions: none');
    if (s.lockRefresh.length) {
      const bad = s.lockRefresh.filter((x) => x.status !== 0);
      console.log(`lock refresh: ${s.lockRefresh.length} dirs (${bad.length} failed)`);
      if (bad.length) failed = true;
    }
    if (s.lockRefreshSkipped.length) {
      console.log(`lock refresh skipped (explicit older pin): ${s.lockRefreshSkipped.length}`);
    }
  }
  if (failed) process.exit(2);
}

main().catch((err) => {
  console.error(err.stack || err);
  process.exit(1);
});
