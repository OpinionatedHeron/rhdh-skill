#!/usr/bin/env node
/*
  Jira PR/MR Web link helper for skill jira-pr-mr-web-link.

  Commands:
    link         Create/update a Web link, apply missing configured defaults, In Progress
    mark-merged  Prefix remotelink titles with "[x] merged: " for merged PRs/MRs

  Auth: $JIRA_API_TOKEN + login/server from ~/.config/.jira/.config.yml
*/

'use strict';

const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

const JIRA_CONFIG = path.join(os.homedir(), '.config', '.jira', '.config.yml');
const USER_CONFIG_DIR = path.join(os.homedir(), '.config', 'jira-pr-mr-link');
const USER_CONFIG_PATH = path.join(USER_CONFIG_DIR, 'config.json');
const LEGACY_USER_CONFIG_PATH = path.join(
  os.homedir(),
  '.config',
  'jira-pr-mr-web-link',
  'config.json',
);
const EXAMPLE_CONFIG_PATH = path.join(__dirname, '..', 'config.example.json');
const SKILL_CONFIG_PATHS = [
  process.env.JIRA_PR_MR_CONFIG,
  USER_CONFIG_PATH,
  LEGACY_USER_CONFIG_PATH,
  path.join(__dirname, '..', 'config.local.json'),
].filter(Boolean);

/** Keys required when applying missing-field defaults (no silent builtins). */
const REQUIRED_DEFAULT_KEYS = [
  'assigneeEmail',
  'teamId',
  'teamName',
  'boardId',
  'storyPoints',
  'priorityName',
  'storyPointsField',
  'teamField',
  'sprintField',
];

const ICONS = {
  gitlab: {
    application: { type: 'com.gitlab', name: 'GitLab' },
    icon: { title: 'GitLab', url16x16: 'https://gitlab.com/favicon.ico' },
  },
  github: {
    application: { type: 'com.github', name: 'GitHub' },
    icon: {
      title: 'GitHub',
      url16x16: 'https://github.githubassets.com/favicons/favicon.png',
    },
  },
};

const LEAVE_STATUS = new Set(['In Progress', 'Review', 'Closed', 'Done']);
const MERGED_PREFIX = '[x] merged: ';

function configurationError(missingKeys, configPath) {
  const missing = missingKeys.join(', ');
  const lines = [
    `Missing Jira PR/MR defaults: ${missing}`,
    '',
    'This skill has no built-in team/assignee values. Configure once:',
    '',
    `  mkdir -p ${USER_CONFIG_DIR}`,
    `  cp ${EXAMPLE_CONFIG_PATH} ${USER_CONFIG_PATH}`,
    `  # edit ${USER_CONFIG_PATH}  (assigneeEmail, teamId, teamName, boardId, …)`,
    '',
    'Or set env vars (JIRA_PR_MR_ASSIGNEE, JIRA_PR_MR_TEAM_ID, JIRA_PR_MR_BOARD_ID, …)',
    'or pass --assignee / --team-id / --board-id / … on the CLI.',
    '',
    'To link without filling defaults: add --no-defaults (or JIRA_PR_MR_APPLY_DEFAULTS=0).',
  ];
  if (configPath) {
    lines.splice(1, 0, `Config loaded from: ${configPath}`);
  }
  return new Error(lines.join('\n'));
}

function usage(exitCode = 0) {
  console.log(`Usage:
  link-pr-mr.js link --issue KEY --url URL --title TITLE [--host gitlab|github]
    [--no-defaults] [--no-comment]
    [--assignee EMAIL] [--team-id ID] [--team-name NAME] [--board-id N]
    [--story-points N] [--priority NAME]

  link-pr-mr.js mark-merged --issue KEY

Environment:
  JIRA_API_TOKEN              required
  JIRA_PR_MR_CONFIG           optional path to JSON config
  JIRA_PR_MR_ASSIGNEE         assignee email
  JIRA_PR_MR_TEAM_ID          Atlassian team UUID
  JIRA_PR_MR_TEAM_NAME        team display name
  JIRA_PR_MR_BOARD_ID         sprint board id
  JIRA_PR_MR_STORY_POINTS     story points (number)
  JIRA_PR_MR_PRIORITY         priority name (e.g. Normal)
  JIRA_PR_MR_APPLY_DEFAULTS   0/false to skip defaults (like --no-defaults)

Config (required for defaults; first found wins):
  $JIRA_PR_MR_CONFIG
  ${USER_CONFIG_PATH}
  <skill>/config.local.json

  Setup:
    mkdir -p ${USER_CONFIG_DIR}
    cp ${EXAMPLE_CONFIG_PATH} ${USER_CONFIG_PATH}

  Jira login/server from ${JIRA_CONFIG}

After link (unless --no-comment), posts/updates a Jira comment:
  PR/MR:
  * <a href="{url}">{repo} #{id}: {title}</a>   (same text as the Web link title)
  Adjusted fields:   (only newly set fields; omitted if none)
`);
  process.exit(exitCode);
}

function parseArgs(argv) {
  const args = { _: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '-h' || a === '--help') {
      usage(0);
    }
    if (a.startsWith('--')) {
      const key = a.slice(2);
      if (key === 'no-defaults') {
        args.noDefaults = true;
        continue;
      }
      if (key === 'no-comment') {
        args.noComment = true;
        continue;
      }
      const val = argv[i + 1];
      if (!val || val.startsWith('--')) {
        throw new Error(`Missing value for --${key}`);
      }
      args[key] = val;
      i += 1;
      continue;
    }
    args._.push(a);
  }
  return args;
}

function readJsonFile(filePath) {
  if (!filePath || !fs.existsSync(filePath)) {
    return null;
  }
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (err) {
    throw new Error(`Invalid JSON config ${filePath}: ${err.message}`);
  }
}

function pickDefined(obj) {
  const out = {};
  for (const [k, v] of Object.entries(obj || {})) {
    if (v !== undefined && v !== null && v !== '') {
      out[k] = v;
    }
  }
  return out;
}

function envNumber(name) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') {
    return undefined;
  }
  const n = Number(raw);
  return Number.isFinite(n) ? n : undefined;
}

function envBoolFalse(name) {
  const raw = (process.env[name] || '').trim().toLowerCase();
  return raw === '0' || raw === 'false' || raw === 'no';
}

function readOptionalSkillConfig() {
  for (const p of SKILL_CONFIG_PATHS) {
    const data = readJsonFile(p);
    if (data) {
      return { path: p, data };
    }
  }
  return { path: null, data: {} };
}

/**
 * Merge defaults: config file < jira CLI board/login hints < env < CLI.
 * No silent team/assignee builtins — missing keys error when applying defaults.
 */
function resolveDefaults(fileCfg, args = {}, { requireComplete = true } = {}) {
  const { path: configPath, data: fileData } = readOptionalSkillConfig();
  const fromFile = pickDefined({
    storyPoints: fileData.storyPoints,
    teamName: fileData.teamName,
    teamId: fileData.teamId,
    boardId: fileData.boardId,
    assigneeEmail: fileData.assigneeEmail,
    priorityName: fileData.priorityName,
    storyPointsField: fileData.storyPointsField,
    teamField: fileData.teamField,
    sprintField: fileData.sprintField,
  });
  const fromJiraCli = pickDefined({
    boardId: fileCfg.boardId,
    assigneeEmail:
      fileCfg.login && String(fileCfg.login).includes('@') ? fileCfg.login : undefined,
  });
  const fromEnv = pickDefined({
    storyPoints: envNumber('JIRA_PR_MR_STORY_POINTS'),
    teamName: process.env.JIRA_PR_MR_TEAM_NAME,
    teamId: process.env.JIRA_PR_MR_TEAM_ID,
    boardId: envNumber('JIRA_PR_MR_BOARD_ID'),
    assigneeEmail: process.env.JIRA_PR_MR_ASSIGNEE,
    priorityName: process.env.JIRA_PR_MR_PRIORITY,
    storyPointsField: process.env.JIRA_PR_MR_STORY_POINTS_FIELD,
    teamField: process.env.JIRA_PR_MR_TEAM_FIELD,
    sprintField: process.env.JIRA_PR_MR_SPRINT_FIELD,
  });
  const fromCli = pickDefined({
    storyPoints:
      args['story-points'] !== undefined ? Number(args['story-points']) : undefined,
    teamName: args['team-name'],
    teamId: args['team-id'],
    boardId: args['board-id'] !== undefined ? Number(args['board-id']) : undefined,
    assigneeEmail: args.assignee,
    priorityName: args.priority,
  });

  const merged = {
    ...fromFile,
    ...fromJiraCli,
    ...fromEnv,
    ...fromCli,
  };
  merged._configPath = configPath;

  if (requireComplete) {
    const missing = REQUIRED_DEFAULT_KEYS.filter((k) => {
      const v = merged[k];
      return v === undefined || v === null || v === '';
    });
    if (missing.length) {
      throw configurationError(missing, configPath);
    }
  }

  return merged;
}

function readJiraConfig() {
  if (!fs.existsSync(JIRA_CONFIG)) {
    throw new Error(`Jira config not found: ${JIRA_CONFIG}`);
  }
  const text = fs.readFileSync(JIRA_CONFIG, 'utf8');
  const login = (text.match(/^login:\s*(.+)$/m) || [])[1]?.trim();
  const server = (text.match(/^server:\s*(.+)$/m) || [])[1]?.trim()?.replace(/\/$/, '');
  if (!login || !server) {
    throw new Error(`Could not parse login/server from ${JIRA_CONFIG}`);
  }
  const boardMatch = text.match(/board:\s*\n\s*id:\s*(\d+)/);
  return {
    login,
    server,
    boardId: boardMatch ? Number(boardMatch[1]) : undefined,
  };
}

function basicAuth(login, token) {
  return `Basic ${Buffer.from(`${login}:${token}`).toString('base64')}`;
}

async function jiraFetch(cfg, method, apiPath, body) {
  const url = `${cfg.server}${apiPath}`;
  const headers = {
    Authorization: basicAuth(cfg.login, cfg.token),
    Accept: 'application/json',
  };
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }
  const res = await fetch(url, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let json;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = text;
  }
  if (!res.ok) {
    const err = new Error(`Jira ${method} ${apiPath} → HTTP ${res.status}: ${text.slice(0, 500)}`);
    err.status = res.status;
    err.body = json;
    throw err;
  }
  return { status: res.status, json };
}

function detectHost(url, explicit) {
  if (explicit === 'gitlab' || explicit === 'github') {
    return explicit;
  }
  if (/github\.com/i.test(url)) {
    return 'github';
  }
  return 'gitlab';
}

function stripMergedPrefix(title) {
  return title
    .replace(/^\[x\]\s*merged:\s*/i, '')
    .replace(/^merged:\s*/i, '')
    .trim();
}

function withMergedPrefix(title) {
  return `${MERGED_PREFIX}${stripMergedPrefix(title)}`;
}

async function getIssueFields(cfg, issue) {
  const d = cfg.defaults;
  const fields = [
    'summary',
    'status',
    'assignee',
    'priority',
    d.storyPointsField,
    d.teamField,
    d.sprintField,
  ].join(',');
  const { json } = await jiraFetch(cfg, 'GET', `/rest/api/3/issue/${issue}?fields=${fields}`);
  return json.fields;
}

async function resolveAssigneeAccountId(cfg, email) {
  const q = encodeURIComponent(email);
  const { json } = await jiraFetch(cfg, 'GET', `/rest/api/3/user/search?query=${q}`);
  if (!Array.isArray(json) || !json[0]?.accountId) {
    throw new Error(`Could not resolve accountId for ${email}`);
  }
  return json[0].accountId;
}

async function resolveActiveSprint(cfg, boardId) {
  const { json } = await jiraFetch(
    cfg,
    'GET',
    `/rest/agile/1.0/board/${boardId}/sprint?state=active`,
  );
  const sprint = json?.values?.[0];
  if (!sprint?.id) {
    throw new Error(`No active sprint on board ${boardId}`);
  }
  return { id: sprint.id, name: sprint.name };
}

function isEmpty(value) {
  if (value === null || value === undefined || value === '') {
    return true;
  }
  if (Array.isArray(value) && value.length === 0) {
    return true;
  }
  return false;
}

async function applyMissingDefaults(cfg, issue, fields) {
  const d = cfg.defaults;
  const summary = {
    storyPoints: 'unchanged',
    team: 'unchanged',
    sprint: 'unchanged',
    assignee: 'unchanged',
    priority: 'unchanged',
  };
  const update = {};

  if (d.storyPoints !== undefined && d.storyPoints !== null && d.storyPoints !== false) {
    if (isEmpty(fields[d.storyPointsField])) {
      update[d.storyPointsField] = d.storyPoints;
      summary.storyPoints = `set ${d.storyPoints}`;
    } else {
      summary.storyPoints = `kept ${fields[d.storyPointsField]}`;
    }
  } else {
    summary.storyPoints = 'skipped (not configured)';
  }

  if (d.teamId) {
    if (isEmpty(fields[d.teamField])) {
      update[d.teamField] = { id: d.teamId };
      summary.team = `set ${d.teamName || d.teamId}`;
    } else {
      summary.team = `kept ${fields[d.teamField].name || fields[d.teamField].id}`;
    }
  } else {
    summary.team = 'skipped (no teamId)';
  }

  if (d.boardId) {
    if (isEmpty(fields[d.sprintField])) {
      try {
        const sprint = await resolveActiveSprint(cfg, d.boardId);
        update[d.sprintField] = sprint.id;
        summary.sprint = `set ${sprint.name}`;
      } catch (err) {
        summary.sprint = `skipped (${err.message})`;
      }
    } else {
      const names = (fields[d.sprintField] || []).map((s) => s.name).join(', ');
      summary.sprint = `kept ${names || 'existing'}`;
    }
  } else {
    summary.sprint = 'skipped (no boardId)';
  }

  if (d.assigneeEmail) {
    if (isEmpty(fields.assignee)) {
      const accountId = await resolveAssigneeAccountId(cfg, d.assigneeEmail);
      update.assignee = { accountId };
      summary.assignee = `set ${d.assigneeEmail}`;
    } else {
      summary.assignee = `kept ${fields.assignee.emailAddress || fields.assignee.displayName}`;
    }
  } else {
    summary.assignee = 'skipped (no assigneeEmail)';
  }

  if (d.priorityName) {
    if (isEmpty(fields.priority)) {
      update.priority = { name: d.priorityName };
      summary.priority = `set ${d.priorityName}`;
    } else {
      summary.priority = `kept ${fields.priority.name}`;
    }
  } else {
    summary.priority = 'skipped (no priorityName)';
  }

  if (Object.keys(update).length > 0) {
    await jiraFetch(cfg, 'PUT', `/rest/api/3/issue/${issue}`, { fields: update });
  }
  return summary;
}

async function transitionInProgress(cfg, issue, currentStatus) {
  if (LEAVE_STATUS.has(currentStatus)) {
    return { status: `kept ${currentStatus}` };
  }
  const { json } = await jiraFetch(cfg, 'GET', `/rest/api/3/issue/${issue}/transitions`);
  const transition = (json.transitions || []).find(
    (t) => t.to?.name === 'In Progress' || t.name === 'In Progress',
  );
  if (!transition) {
    return { status: `no In Progress transition from ${currentStatus}` };
  }
  await jiraFetch(cfg, 'POST', `/rest/api/3/issue/${issue}/transitions`, {
    transition: { id: transition.id },
  });
  return { status: `transitioned ${currentStatus} → In Progress` };
}

async function upsertRemoteLink(cfg, issue, { url, title, host }) {
  const iconCfg = ICONS[host];
  const { json: existing } = await jiraFetch(cfg, 'GET', `/rest/api/3/issue/${issue}/remotelink`);
  const match = (existing || []).find((l) => l.object?.url === url);
  const payload = {
    application: iconCfg.application,
    object: {
      url,
      title,
      icon: iconCfg.icon,
    },
  };
  if (match?.id) {
    await jiraFetch(cfg, 'PUT', `/rest/api/3/issue/${issue}/remotelink/${match.id}`, payload);
    return { action: 'updated', id: match.id, title };
  }
  const { json } = await jiraFetch(cfg, 'POST', `/rest/api/3/issue/${issue}/remotelink`, payload);
  return { action: 'created', id: json?.id, title };
}

function printLinkSummary(result) {
  console.log(`issue: ${result.issue}`);
  console.log(`webLink: ${result.webLink.action} — ${result.webLink.title}`);
  console.log(`url: ${result.url}`);
  console.log(`status: ${result.status}`);
  if (result.defaults) {
    console.log('defaults:');
    for (const [k, v] of Object.entries(result.defaults)) {
      console.log(`  ${k}: ${v}`);
    }
  }
  if (result.comment) {
    console.log(`comment: ${result.comment}`);
  }
}

function adfParagraph(text) {
  return {
    type: 'paragraph',
    content: text ? [{ type: 'text', text }] : [],
  };
}

function adfBulletList(items) {
  return {
    type: 'bulletList',
    content: items.map((text) => ({
      type: 'listItem',
      content: [adfParagraph(text)],
    })),
  };
}

function adfPrMrBullet(url, linkTitle) {
  return {
    type: 'bulletList',
    content: [
      {
        type: 'listItem',
        content: [
          {
            type: 'paragraph',
            content: [
              {
                type: 'text',
                text: linkTitle,
                marks: [{ type: 'link', attrs: { href: url } }],
              },
            ],
          },
        ],
      },
    ],
  };
}

/** Human title from linker title `repo #N: <title>` (optional `[x] merged: ` prefix). */
function displayTitleFromLinkTitle(title) {
  return (
    String(title || '')
      .replace(/^\[x\]\s*merged:\s*/i, '')
      .replace(/^[^#\n]+#\d+:\s*/, '')
      .trim() || String(title || '').trim()
  );
}

const ADJUSTED_FIELD_LABELS = {
  storyPoints: 'Story points',
  team: 'Team',
  sprint: 'Sprint',
  assignee: 'Assignee',
  priority: 'Priority',
};

/** Only fields newly set by this run (ignore kept/unchanged). */
function collectAdjustedFieldLines(defaults, statusLine) {
  const items = [];
  if (defaults) {
    for (const [key, value] of Object.entries(defaults)) {
      if (typeof value === 'string' && value.startsWith('set ')) {
        const label = ADJUSTED_FIELD_LABELS[key] || key;
        items.push(`${label}: ${value.slice(4)}`);
      }
    }
  }
  if (typeof statusLine === 'string' && statusLine.startsWith('transitioned ')) {
    const to = (statusLine.match(/→\s*(.+)$/) || [])[1]?.trim() || 'In Progress';
    items.push(`Status: ${to}`);
  }
  return items;
}

function buildLinkCommentAdf({ url, webLink, status, defaults }) {
  // Visible text matches the Jira remote Web link title: `repo #N: <title>`
  // ADF: <a href="{url}">{repo} #{id}: {title}</a>
  const linkTitle =
    String(webLink?.title || '')
      .replace(/^\[x\]\s*merged:\s*/i, '')
      .trim() || displayTitleFromLinkTitle(webLink?.title) || url;
  const content = [adfParagraph('PR/MR:'), adfPrMrBullet(url, linkTitle)];
  const adjusted = collectAdjustedFieldLines(defaults, status);
  if (adjusted.length > 0) {
    content.push(adfParagraph('Adjusted fields:'));
    content.push(adfBulletList(adjusted));
  }
  return { type: 'doc', version: 1, content };
}

async function findCommentMentioningUrl(cfg, issue, url) {
  const { json } = await jiraFetch(cfg, 'GET', `/rest/api/3/issue/${issue}/comment`);
  const comments = json?.comments || [];
  // Prefer the latest comment that mentions this PR/MR URL
  for (let i = comments.length - 1; i >= 0; i -= 1) {
    const c = comments[i];
    if (JSON.stringify(c.body || '').includes(url)) {
      return c;
    }
  }
  return null;
}

async function postLinkComment(cfg, issue, { url, webLink, status, defaults }) {
  const body = buildLinkCommentAdf({ url, webLink, status, defaults });
  const existing = await findCommentMentioningUrl(cfg, issue, url);
  if (existing?.id) {
    await jiraFetch(cfg, 'PUT', `/rest/api/3/issue/${issue}/comment/${existing.id}`, {
      body,
    });
    return `updated id=${existing.id}`;
  }
  const { json } = await jiraFetch(cfg, 'POST', `/rest/api/3/issue/${issue}/comment`, {
    body,
  });
  return json?.id ? `posted id=${json.id}` : 'posted';
}

async function cmdLink(args, cfg) {
  const issue = args.issue;
  const url = args.url;
  const title = args.title;
  if (!issue || !url || !title) {
    throw new Error('link requires --issue, --url, and --title');
  }
  const host = detectHost(url, args.host);
  const webLink = await upsertRemoteLink(cfg, issue, { url, title, host });

  const skipDefaults = args.noDefaults || envBoolFalse('JIRA_PR_MR_APPLY_DEFAULTS');
  let defaults;
  let statusLine;
  if (!skipDefaults) {
    const fields = await getIssueFields(cfg, issue);
    defaults = await applyMissingDefaults(cfg, issue, fields);
    const statusResult = await transitionInProgress(cfg, issue, fields.status?.name || '');
    statusLine = statusResult.status;
  } else {
    statusLine = 'skipped (--no-defaults)';
  }

  let commentLine;
  if (!args.noComment) {
    try {
      commentLine = await postLinkComment(cfg, issue, {
        url,
        webLink,
        status: statusLine,
        defaults,
      });
    } catch (err) {
      commentLine = `failed — ${err.message}`;
    }
  } else {
    commentLine = 'skipped (--no-comment)';
  }

  printLinkSummary({
    issue,
    url,
    webLink,
    status: statusLine,
    defaults,
    comment: commentLine,
  });
}

function parsePrMrUrl(url) {
  let m = url.match(/github\.com\/([^/]+)\/([^/]+)\/pull\/(\d+)/i);
  if (m) {
    return { kind: 'github', owner: m[1], repo: m[2], id: m[3] };
  }
  // Capture host so glab targets gitlab.cee.redhat.com (not default gitlab.com).
  m = url.match(/https?:\/\/(gitlab[^/]*)\/(.+?)\/-\/merge_requests\/(\d+)/i);
  if (m) {
    return { kind: 'gitlab', host: m[1], project: m[2], id: m[3] };
  }
  return null;
}

function isMerged(ref) {
  if (ref.kind === 'github') {
    const label = `${ref.owner}/${ref.repo}#${ref.id}`;
    const out = spawnSync(
      'gh',
      ['api', `repos/${ref.owner}/${ref.repo}/pulls/${ref.id}`, '--jq', '.merged'],
      { encoding: 'utf8' },
    );
    if (out.status !== 0) {
      const err = (out.stderr || out.stdout || '').trim().slice(0, 240);
      console.error(`warn: merge-check failed for github ${label}: ${err || `exit ${out.status}`}`);
      return false;
    }
    return String(out.stdout).trim() === 'true';
  }
  const label = `${ref.project}!${ref.id}`;
  const project = encodeURIComponent(ref.project);
  const glabArgs = ['api'];
  if (ref.host) {
    glabArgs.push('--hostname', ref.host);
  }
  glabArgs.push(`projects/${project}/merge_requests/${ref.id}`);
  const out = spawnSync('glab', glabArgs, { encoding: 'utf8' });
  if (out.status !== 0) {
    const err = (out.stderr || out.stdout || '').trim().slice(0, 240);
    console.error(`warn: merge-check failed for gitlab ${label}: ${err || `exit ${out.status}`}`);
    return false;
  }
  try {
    const mr = JSON.parse(out.stdout);
    return Boolean(mr.merged_at) || mr.state === 'merged';
  } catch (err) {
    console.error(`warn: merge-check parse failed for gitlab ${label}: ${err.message}`);
    return false;
  }
}

async function cmdMarkMerged(args, cfg) {
  const issue = args.issue;
  if (!issue) {
    throw new Error('mark-merged requires --issue');
  }
  const { json: links } = await jiraFetch(cfg, 'GET', `/rest/api/3/issue/${issue}/remotelink`);
  const updated = [];
  const leftOpen = [];
  const skipped = [];

  for (const link of links || []) {
    const url = link.object?.url;
    const title = link.object?.title || '';
    if (!url) {
      continue;
    }
    const ref = parsePrMrUrl(url);
    if (!ref) {
      skipped.push(title || url);
      continue;
    }
    if (!isMerged(ref)) {
      leftOpen.push({ title: title || url, url });
      continue;
    }
    const newTitle = withMergedPrefix(title);
    if (newTitle === title) {
      updated.push({ label: `already: ${title}`, url });
      continue;
    }
    const host = ref.kind === 'github' ? 'github' : 'gitlab';
    const iconCfg = ICONS[host];
    await jiraFetch(cfg, 'PUT', `/rest/api/3/issue/${issue}/remotelink/${link.id}`, {
      application: iconCfg.application,
      object: {
        url,
        title: newTitle,
        icon: iconCfg.icon,
        status: { resolved: true },
      },
    });
    updated.push({ label: newTitle, url });
  }

  console.log(`issue: ${issue}`);
  console.log(`updated: ${updated.length}`);
  for (const item of updated) {
    console.log(`  ${item.label}`);
    console.log(`    ${item.url}`);
  }
  console.log(`leftOpen: ${leftOpen.length}`);
  for (const item of leftOpen) {
    console.log(`  ${item.title}`);
    console.log(`    ${item.url}`);
  }
  if (skipped.length) {
    console.log(`skippedNonPrMr: ${skipped.length}`);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const cmd = args._[0];
  if (!cmd) {
    usage(1);
  }
  if (!process.env.JIRA_API_TOKEN) {
    throw new Error('JIRA_API_TOKEN is not set');
  }
  const fileCfg = readJiraConfig();
  const skipDefaults =
    cmd !== 'link' || args.noDefaults || envBoolFalse('JIRA_PR_MR_APPLY_DEFAULTS');
  const defaults = resolveDefaults(fileCfg, args, { requireComplete: !skipDefaults });
  const cfg = {
    login: fileCfg.login,
    server: fileCfg.server,
    boardId: defaults.boardId,
    token: process.env.JIRA_API_TOKEN,
    defaults,
  };

  if (cmd === 'link') {
    await cmdLink(args, cfg);
    return;
  }
  if (cmd === 'mark-merged') {
    await cmdMarkMerged(args, cfg);
    return;
  }
  throw new Error(`Unknown command: ${cmd}`);
}

main().catch((err) => {
  console.error(`[ERROR] ${err.message}`);
  process.exit(1);
});
