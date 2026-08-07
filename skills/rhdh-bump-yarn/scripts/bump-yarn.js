#!/usr/bin/env node
/*
  Bump Yarn Berry across one or more RHDH-related checkouts.

  Mirrors the RHIDP-16074 / rhdh-plugins#2918 pattern:
    - download yarn-<to>.cjs from yarnpkg/berry
    - replace matching .yarn/releases/yarn-<from>.cjs binaries
    - rewrite yarnPath / packageManager / "yarn set version" / ENV YARN= pins

  By default, refreshes yarn.lock via `yarn install --mode=update-lockfile`
  for every lock that will run under --to yarn — including nested workspaces
  that inherit a root yarnPath / packageManager (not only dirs whose pins
  were rewritten). Skips locks with an explicit pin outside --from/--to
  (e.g. roadie 4.9.2, backstage 4.8.1, dcm 4.15.0) and dist-dynamic
  artifacts. New yarn-*.cjs binaries are chmod +x (100755). A full five-repo
  lock regen can take >45 minutes. Use --no-refresh-locks to skip.

  Usage:
    bump-yarn.js --to 4.17.1 [--from 4.12.0,4.14.1] --root PATH [--root PATH ...]
    bump-yarn.js --scan --root PATH
    bump-yarn.js --fetch-only --to 4.17.1
    bump-yarn.js --to 4.17.1 --root PATH --dry-run
    bump-yarn.js --to 4.17.1 --root PATH --no-refresh-locks
*/

'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const https = require('node:https');
const http = require('node:http');

const DEFAULT_FROM = ['4.12.0', '4.14.1'];
const CACHE_DIR = path.join(os.homedir(), '.cache', 'rhdh-bump-yarn');

const TEXT_BASENAMES = new Set([
  'package.json',
  '.yarnrc.yml',
  'Containerfile',
  'Dockerfile',
  'run-e2e.sh',
]);

function usage(exitCode = 0) {
  console.log(`Usage:
  bump-yarn.js --to VERSION [--from V1,V2] --root PATH [--root PATH ...]
  bump-yarn.js --scan --root PATH [--root PATH ...]
  bump-yarn.js --fetch-only --to VERSION
  bump-yarn.js --to VERSION --root PATH --dry-run
  bump-yarn.js --to VERSION --root PATH --no-refresh-locks

Defaults:
  --from  ${DEFAULT_FROM.join(',')}
  refresh yarn.lock for all workspaces using --to (incl. inherited root pin);
  skip explicit older pins and dist-dynamic; opt out with --no-refresh-locks
  binaries written mode 0755; Binary cache: ${CACHE_DIR}

Examples (RHIDP-16074 five-repo set):
  node skills/rhdh-bump-yarn/scripts/bump-yarn.js --to 4.17.1 \\
    --root ~/path/rhdh-plugins --root ~/path/rhdh \\
    --root ~/path/overlays --root ~/path/rhdh-downstream \\
    --root ~/path/rhdh-plugin-catalog

Known repo shapes (any checkout root works; discovery is recursive):
  rhdh-plugins          root .yarn + packageManager + yarnPath
  rhdh (GH midstream)   root/.ci/dynamic-plugins/e2e + Containerfile
  overlays              packageManager pins (+ rare releases)
  rhdh (GL downstream)  distgit/containers/rhdh-hub + Containerfile
  rhdh-plugin-catalog   workspaces/*/.yarn + builder.Containerfile + overlay-repo
`);
  process.exit(exitCode);
}

function parseArgs(argv) {
  const args = {
    from: [...DEFAULT_FROM],
    roots: [],
    to: null,
    scan: false,
    fetchOnly: false,
    dryRun: false,
    refreshLocks: true,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '-h' || a === '--help') usage(0);
    if (a === '--scan') {
      args.scan = true;
      continue;
    }
    if (a === '--fetch-only') {
      args.fetchOnly = true;
      continue;
    }
    if (a === '--dry-run') {
      args.dryRun = true;
      continue;
    }
    if (a === '--no-refresh-locks') {
      args.refreshLocks = false;
      continue;
    }
    if (a === '--refresh-locks') {
      // default; kept for explicit/compat
      args.refreshLocks = true;
      continue;
    }
    if (a === '--to') {
      args.to = argv[++i];
      continue;
    }
    if (a === '--from') {
      args.from = String(argv[++i] || '')
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      continue;
    }
    if (a === '--root') {
      args.roots.push(path.resolve(argv[++i]));
      continue;
    }
    console.error(`Unknown arg: ${a}`);
    usage(1);
  }
  return args;
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function yarnReleaseUrl(version) {
  // Tag is @yarnpkg/cli/<version>; encode for raw.githubusercontent.com
  const tag = encodeURIComponent(`@yarnpkg/cli/${version}`);
  return `https://raw.githubusercontent.com/yarnpkg/berry/${tag}/packages/yarnpkg-cli/bin/yarn.js`;
}

function download(url, dest) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https:') ? https : http;
    const req = client.get(url, { headers: { 'User-Agent': 'rhdh-bump-yarn' } }, (res) => {
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
      out.on('finish', () => {
        out.close(() => {
          fs.renameSync(tmp, dest);
          resolve(dest);
        });
      });
      out.on('error', reject);
    });
    req.on('error', reject);
  });
}

function makeExecutable(filePath) {
  try {
    fs.chmodSync(filePath, 0o755);
  } catch (err) {
    console.error(`warn: chmod +x failed for ${filePath}: ${err.message}`);
  }
}

function ensureBinary(version, { force = false } = {}) {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  const dest = path.join(CACHE_DIR, `yarn-${version}.cjs`);
  if (!force && fs.existsSync(dest)) {
    const v = spawnSync(process.execPath, [dest, '-v'], { encoding: 'utf8' });
    if (v.status === 0 && String(v.stdout).trim() === version) {
      makeExecutable(dest);
      return dest;
    }
  }
  const url = yarnReleaseUrl(version);
  console.log(`fetch: ${url}`);
  return download(url, dest).then(() => {
    makeExecutable(dest);
    const v = spawnSync(process.execPath, [dest, '-v'], { encoding: 'utf8' });
    if (v.status !== 0 || String(v.stdout).trim() !== version) {
      throw new Error(
        `Downloaded yarn binary version mismatch: got ${JSON.stringify(String(v.stdout).trim())} expected ${version}`,
      );
    }
    console.log(`cached: ${dest} (${fs.statSync(dest).size} bytes)`);
    return dest;
  });
}

function shouldSkipDir(name) {
  return (
    name === '.git' ||
    name === 'node_modules' ||
    name === '.yarn' || // still walk releases via dedicated find
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
        if (shouldSkipDir(ent.name)) {
          // Still descend into .yarn/releases only
          if (ent.name === '.yarn') {
            const releases = path.join(full, 'releases');
            if (fs.existsSync(releases)) stack.push(releases);
          }
          continue;
        }
        stack.push(full);
      } else if (ent.isFile()) {
        onFile(full, ent.name);
      }
    }
  }
}

function isTextCandidate(full, basename) {
  if (TEXT_BASENAMES.has(basename)) return true;
  if (basename.endsWith('.Containerfile')) return true;
  if (basename.endsWith('.Dockerfile')) return true;
  // Embedded packageManager JSON snippets sometimes live in shell helpers
  if (basename.endsWith('.sh') && /e2e|yarn|packageManager/i.test(basename + full)) return true;
  return false;
}

function scanRoot(root) {
  const releases = [];
  const pins = [];
  walk(root, (full, basename) => {
    const m = /^yarn-([0-9]+\.[0-9]+\.[0-9]+)\.cjs$/.exec(basename);
    if (m && full.includes(`${path.sep}.yarn${path.sep}releases${path.sep}`)) {
      releases.push({ path: full, version: m[1] });
      return;
    }
    if (!isTextCandidate(full, basename)) return;
    let text;
    try {
      text = fs.readFileSync(full, 'utf8');
    } catch {
      return;
    }
    if (text.length > 2_000_000) return;
    const found = new Set();
    for (const re of [
      /yarn@([0-9]+\.[0-9]+\.[0-9]+)/g,
      /yarn-([0-9]+\.[0-9]+\.[0-9]+)\.cjs/g,
      /yarn set version ([0-9]+\.[0-9]+\.[0-9]+)/g,
    ]) {
      let match;
      while ((match = re.exec(text))) found.add(match[1]);
    }
    if (found.size) pins.push({ path: full, versions: [...found].sort() });
  });
  return { releases, pins };
}

function bumpText(content, fromVersions, toVersion) {
  const fromAlt = fromVersions.map(escapeRegExp).join('|');
  let next = content;
  next = next.replace(
    new RegExp(`yarn-(?:${fromAlt})\\.cjs`, 'g'),
    `yarn-${toVersion}.cjs`,
  );
  next = next.replace(
    new RegExp(`"packageManager":\\s*"yarn@(?:${fromAlt})"`, 'g'),
    `"packageManager": "yarn@${toVersion}"`,
  );
  // Corepack form with integrity suffix
  next = next.replace(
    new RegExp(`"packageManager":\\s*"yarn@(?:${fromAlt})\\+[^"]+"`, 'g'),
    `"packageManager": "yarn@${toVersion}"`,
  );
  next = next.replace(
    new RegExp(`yarn set version (?:${fromAlt})\\b`, 'g'),
    `yarn set version ${toVersion}`,
  );
  return next;
}

function readExplicitYarnPin(dir) {
  // Only packageManager / yarnPath — avoid matching unrelated yarn@x.y.z deps.
  const pkgPath = path.join(dir, 'package.json');
  if (fs.existsSync(pkgPath)) {
    try {
      const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf8'));
      const pm = pkg.packageManager;
      if (typeof pm === 'string') {
        const m = /^yarn@([0-9]+\.[0-9]+\.[0-9]+)/.exec(pm);
        if (m) return m[1];
      }
    } catch {
      // ignore malformed package.json
    }
  }
  const rcPath = path.join(dir, '.yarnrc.yml');
  if (fs.existsSync(rcPath)) {
    try {
      const text = fs.readFileSync(rcPath, 'utf8');
      const m = /(?:^|\n)yarnPath:\s*.*yarn-([0-9]+\.[0-9]+\.[0-9]+)\.cjs/.exec(text);
      if (m) return m[1];
    } catch {
      // ignore
    }
  }
  return null;
}

function shouldSkipLockPath(lockPath) {
  const parts = lockPath.split(path.sep);
  if (parts.includes('node_modules')) return true;
  if (parts.includes('dist-dynamic')) return true;
  if (parts.includes('.git')) return true;
  return false;
}

function collectLockRefreshDirs(root, { from, to }) {
  const fromSet = new Set(from);
  const dirs = [];
  const skipped = [];
  walk(root, (full, basename) => {
    if (basename !== 'yarn.lock') return;
    if (shouldSkipLockPath(full)) return;
    const dir = path.dirname(full);
    const pin = readExplicitYarnPin(dir);
    // Explicit pin outside --from/--to → leave alone (roadie/backstage/dcm, etc.)
    if (pin && pin !== to && !fromSet.has(pin)) {
      skipped.push({ dir, pin });
      return;
    }
    dirs.push(dir);
  });
  dirs.sort();
  return { dirs, skipped };
}

function resolveYarnBin(dir, binaryPath, toVersion) {
  const newName = `yarn-${toVersion}.cjs`;
  const local = path.join(dir, '.yarn', 'releases', newName);
  if (fs.existsSync(local)) return local;
  let cur = dir;
  for (let i = 0; i < 8; i += 1) {
    const candidate = path.join(cur, '.yarn', 'releases', newName);
    if (fs.existsSync(candidate)) return candidate;
    const parent = path.dirname(cur);
    if (parent === cur) break;
    cur = parent;
  }
  return binaryPath;
}

function bumpRoot(root, { from, to, binaryPath, dryRun, refreshLocks }) {
  const summary = {
    root,
    binariesReplaced: [],
    filesUpdated: [],
    skippedReleases: [],
    remaining: [],
    lockRefresh: [],
    lockRefreshSkipped: [],
  };

  const fromSet = new Set(from);
  const newName = `yarn-${to}.cjs`;

  // 1) binaries
  walk(root, (full, basename) => {
    const m = /^yarn-([0-9]+\.[0-9]+\.[0-9]+)\.cjs$/.exec(basename);
    if (!m || !full.includes(`${path.sep}.yarn${path.sep}releases${path.sep}`)) return;
    const ver = m[1];
    if (!fromSet.has(ver)) {
      if (ver !== to) summary.skippedReleases.push({ path: full, version: ver });
      return;
    }
    const dest = path.join(path.dirname(full), newName);
    summary.binariesReplaced.push({ from: full, to: dest, version: ver });
    if (dryRun) return;
    fs.copyFileSync(binaryPath, dest);
    makeExecutable(dest);
    if (path.resolve(full) !== path.resolve(dest)) fs.unlinkSync(full);
  });

  // 2) text pins
  walk(root, (full, basename) => {
    if (!isTextCandidate(full, basename)) return;
    let text;
    try {
      text = fs.readFileSync(full, 'utf8');
    } catch {
      return;
    }
    if (text.length > 2_000_000) return;
    const next = bumpText(text, from, to);
    if (next === text) return;
    summary.filesUpdated.push(full);
    if (!dryRun) fs.writeFileSync(full, next);
  });

  // 3) remaining inventory (from-set only) — skip on dry-run (tree unchanged)
  if (!dryRun) {
    const after = scanRoot(root);
    for (const r of after.releases) {
      if (fromSet.has(r.version)) summary.remaining.push(`release ${r.version}: ${r.path}`);
    }
    for (const p of after.pins) {
      const leftover = p.versions.filter((v) => fromSet.has(v));
      if (leftover.length) summary.remaining.push(`${leftover.join(',')}: ${p.path}`);
    }
  }

  // 4) lock refresh — every yarn.lock that will run under --to (incl. inherited root pin)
  if (refreshLocks && !dryRun) {
    const { dirs, skipped } = collectLockRefreshDirs(root, { from, to });
    summary.lockRefreshSkipped = skipped;
    for (const s of skipped) {
      console.log(`refresh-locks: skip ${s.dir} (explicit pin ${s.pin})`);
    }
    for (const dir of dirs) {
      const yarnBin = resolveYarnBin(dir, binaryPath, to);
      console.log(`refresh-locks: ${dir}`);
      const r = spawnSync(
        process.execPath,
        [yarnBin, 'install', '--mode=update-lockfile'],
        {
          cwd: dir,
          encoding: 'utf8',
          env: { ...process.env, YARN_ENABLE_IMMUTABLE_INSTALLS: 'false' },
          stdio: ['ignore', 'pipe', 'pipe'],
        },
      );
      // Drop untracked .yarnrc.yml yarn may invent during "migration"
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
      summary.lockRefresh.push({
        dir,
        status: r.status,
        stderr: (r.stderr || '').split('\n').slice(-5).join('\n'),
      });
      if (r.status !== 0) {
        console.error(`warn: yarn install failed in ${dir} (exit ${r.status})`);
      }
    }
  }

  return summary;
}

function printScan(root) {
  const { releases, pins } = scanRoot(root);
  const byVer = new Map();
  for (const r of releases) {
    byVer.set(r.version, (byVer.get(r.version) || 0) + 1);
  }
  console.log(`\n=== scan ${root} ===`);
  console.log('releases:');
  for (const [v, n] of [...byVer.entries()].sort()) console.log(`  yarn-${v}.cjs × ${n}`);
  if (!releases.length) console.log('  (none)');
  console.log('text pins (packageManager / yarnPath / yarn set version):');
  const pinByVer = new Map();
  for (const p of pins) {
    for (const v of p.versions) pinByVer.set(v, (pinByVer.get(v) || 0) + 1);
  }
  for (const [v, n] of [...pinByVer.entries()].sort()) console.log(`  ${v} × ${n} files`);
  if (!pins.length) console.log('  (none)');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.fetchOnly) {
    if (!args.to) {
      console.error('--fetch-only requires --to');
      usage(1);
    }
    await ensureBinary(args.to, { force: true });
    return;
  }

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

  const binaryPath = await ensureBinary(args.to);
  console.log(`to: ${args.to}`);
  console.log(`from: ${args.from.join(', ')}`);
  console.log(`dry-run: ${args.dryRun}`);
  console.log(`refresh-locks: ${args.refreshLocks}`);

  let failed = false;
  for (const root of args.roots) {
    const summary = bumpRoot(root, {
      from: args.from,
      to: args.to,
      binaryPath,
      dryRun: args.dryRun,
      refreshLocks: args.refreshLocks,
    });
    console.log(`\n=== ${args.dryRun ? 'dry-run ' : ''}bump ${root} ===`);
    console.log(`binaries: ${summary.binariesReplaced.length}`);
    for (const b of summary.binariesReplaced.slice(0, 30)) {
      console.log(`  ${b.version} → ${b.to}`);
    }
    if (summary.binariesReplaced.length > 30) {
      console.log(`  … +${summary.binariesReplaced.length - 30} more`);
    }
    const relFiles = summary.filesUpdated
      .map((f) => path.relative(root, f))
      .sort();
    console.log(`files: ${relFiles.length}`);
    for (const f of relFiles) console.log(`  ${f}`);
    if (summary.skippedReleases.length) {
      console.log(`left alone (not in --from):`);
      const counts = new Map();
      for (const s of summary.skippedReleases) {
        counts.set(s.version, (counts.get(s.version) || 0) + 1);
      }
      for (const [v, n] of [...counts.entries()].sort()) console.log(`  yarn-${v}.cjs × ${n}`);
    }
    if (summary.remaining.length) {
      failed = true;
      console.log('REMAINING from-versions (unexpected):');
      for (const line of summary.remaining) console.log(`  ${line}`);
    } else {
      console.log('remaining from-versions: none');
    }
    if (summary.lockRefresh.length) {
      const bad = summary.lockRefresh.filter((x) => x.status !== 0);
      console.log(`lock refresh: ${summary.lockRefresh.length} dirs (${bad.length} failed)`);
      if (bad.length) failed = true;
    }
    if (summary.lockRefreshSkipped?.length) {
      console.log(`lock refresh skipped (explicit older pin): ${summary.lockRefreshSkipped.length}`);
      for (const s of summary.lockRefreshSkipped.slice(0, 20)) {
        console.log(`  ${s.pin}: ${path.relative(root, s.dir)}`);
      }
      if (summary.lockRefreshSkipped.length > 20) {
        console.log(`  … +${summary.lockRefreshSkipped.length - 20} more`);
      }
    }
  }

  if (failed) process.exit(2);
}

main().catch((err) => {
  console.error(err.stack || err);
  process.exit(1);
});
