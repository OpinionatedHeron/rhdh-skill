# Workflow: Migrate a Frontend Plugin to NFS

<essential_principles>

<principle name="discover_first">
Always read the plugin's `package.json`, `src/plugin.ts` (or `src/plugin.tsx`), route refs, API factories, and exported components before making any changes. Understand what exists before migrating.
</principle>

<principle name="nfs_at_alpha">
NFS is not GA yet. The default approach is to add NFS at `./alpha` while keeping legacy at the root export (`.`). This avoids breaking existing consumers.
</principle>

<principle name="upstream_apis">
Use `@backstage/frontend-plugin-api` for core blueprints. RHDH-specific blueprints (`AppDrawerContentBlueprint`, `GlobalHeaderMenuItemBlueprint`) come from `@red-hat-developer-hub/*` packages. Don't mix them up.
</principle>

<principle name="modules_not_plugins">
Entity content and cards can go directly in the plugin's `extensions` array — the blueprint declares its own attach point. Use `createFrontendModule` only for extensions that target a different plugin (translations → `pluginId: 'app'`, homepage widgets → `pluginId: 'home'`) or when injecting content from outside a plugin you don't own.
</principle>

<principle name="shared_components">
Keep component imports (`useApi`, `useRouteRef`, etc.) on `@backstage/core-plugin-api` — they work in both legacy and NFS contexts. This lets the same components serve both export paths. Only use `compatWrapper()` when a component depends on legacy context providers (e.g. old `SidebarContext`) that aren't available in NFS. Don't migrate component imports to `@backstage/frontend-plugin-api` if you need to support legacy consumers.
</principle>

<principle name="keep_legacy">
Legacy exports must remain available since NFS is not GA. With the alpha approach, legacy stays at root unchanged. With the colocated approach, legacy source moves to `legacy.ts` but is re-exported from `index.ts` so existing consumers don't break.
</principle>

</essential_principles>

<intake>

## What would you like to do?

1. **Migrate a plugin to NFS** — Analyze your existing plugin and convert it to the New Frontend System
2. **Test a migrated plugin in RHDH** — Deploy and verify in a local or cluster RHDH instance
3. **Learn about NFS migration** — Read the migration guide

**Wait for response before proceeding.**

</intake>

<routing>

| Response | Action |
|----------|--------|
| 1, "migrate", "convert", "NFS" | Follow the migration workflow below |
| 2, "test", "verify", "deploy" | Read `workflows/test-nfs-plugin.md` |
| 3, "learn", "guide", "overview" | Read `references/overview.md` and present key sections to the user |

</routing>

<migration_workflow>

### Step 1: Discover

Read `package.json` and `src/plugin.ts` (or `src/plugin.tsx`). Identify:

- Plugin ID
- Routes and route refs
- API factories
- Routable extensions (pages)
- Component extensions (entity cards, tabs)
- Sidebar/nav items
- Translations
- RHDH-specific extensions (drawers, header items, homepage widgets)
- RHDH dynamic plugin mount points (`app-config.dynamic.yaml` — see `references/mount-point-mapping.md`)

List all findings to the user before proceeding.

If the plugin's `@backstage/*` dependencies are outdated, invoke
`/rhdh-backstage-upgrade` by name and return here once the versions are in
place. That skill owns version numbers; this workflow owns extension shape.

### Step 2: Choose Approach

NFS is not GA yet. Use the **Alpha** approach by default: NFS at `./alpha`, legacy stays at root (`.`).

The **Colocated** approach is the alternative: NFS as default export in `index.ts`, legacy source in `legacy.ts` but re-exported from `index.ts` for backward compatibility. Use this when the user wants NFS and legacy APIs available from the same import path.

### Step 3: Migrate Extensions

For each extension type found in Step 1, load the appropriate reference:

| Extension type | Reference to load |
|----------------|-------------------|
| Pages, API factories | `references/migrate-page.md` |
| Entity content tabs or cards | `references/migrate-entity-content.md` |
| Translations / i18n | `references/migrate-translations.md` |
| RHDH drawers, header items, homepage widgets | `references/migrate-rhdh-extensions.md` |
| App-level wrappers or root elements | `references/migrate-app-level.md` |

Apply each reference's patterns to the discovered extensions. For page plugins, create NFS variants of page components without the page shell (dual header pattern in `migrate-page.md`).

### Step 4: Update package.json

Load `references/package-json.md` and apply the export configuration matching the chosen approach (alpha or colocated).

### Step 5: Update App Wiring

Load `references/app-setup.md` and:

- Add an NFS dev app at `dev/index.tsx` (or `dev/nfs.tsx`) using `createApp` from `@backstage/frontend-defaults`
- Keep the existing legacy dev app working
- Verify consumer imports still resolve (alpha approach: no changes needed; colocated approach: legacy re-exports from `index.ts` maintain compatibility)

### Step 6: Verify

Load `references/verification.md` and run all checks. Run `yarn tsc` from the **workspace root** (not just the plugin directory) to catch consumer import issues.

</migration_workflow>

<reference_index>

| Reference | Load when... |
|-----------|-------------|
| `references/migrate-page.md` | Plugin has pages or API factories |
| `/rhdh-backstage-api-changes` (invoke by name) | Updating a plugin migrated against an older NFS version |
| `references/migrate-entity-content.md` | Plugin has entity tabs or cards |
| `references/migrate-translations.md` | Plugin has i18n/translations |
| `references/migrate-rhdh-extensions.md` | Plugin uses RHDH drawer, header, or homepage widgets |
| `references/mount-point-mapping.md` | Plugin uses RHDH dynamic plugin mount points (legacy config) |
| `references/migrate-app-level.md` | Plugin has app-level wrappers or root elements |
| `references/package-json.md` | Updating package.json exports |
| `references/app-setup.md` | Setting up or updating the NFS dev app |
| `references/verification.md` | Verifying the migration |
| `references/testing-rhdh.md` | Testing with a real RHDH instance |
| `references/gotchas.md` | Troubleshooting migration issues |
| `references/reference-prs.md` | Looking for real migration examples |
| `references/operator-config.md` | Plugin uses RHDH operator config or needs `app.extensions` / `app.routes.bindings` reference |
| `references/overview.md` | User wants to learn about NFS before migrating |
| `references/support.md` | User needs help beyond what the skill covers |

</reference_index>

<success_criteria>

- `./alpha` (or root, for colocated) default-exports a `createFrontendPlugin` result
- All legacy extensions have NFS Blueprint equivalents
- Pages that need nav entries have `title` and `icon` set (on `PageBlueprint` or `createFrontendPlugin`)
- `package.json` exports NFS at `./alpha` (alpha approach) or `.` (colocated approach)
- Translations are in a `createFrontendModule` with `pluginId: 'app'`
- Entity content extensions are in the plugin's `extensions` array (or a catalog module if injecting from outside)
- `yarn tsc` and `yarn build` pass
- Legacy exports remain available (unchanged at root for alpha; re-exported from `index.ts` for colocated)

</success_criteria>
