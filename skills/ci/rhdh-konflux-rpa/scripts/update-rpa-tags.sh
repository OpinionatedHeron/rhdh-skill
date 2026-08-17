#!/usr/bin/env bash
# Bump RHDH ReleasePlanAdmission tag versions in konflux-release-data.
# SPDX-License-Identifier: EPL-2.0

set -euo pipefail

NEW_VERSION=""
REPO_DIR=""
RPA_DIR=""

readonly RPA_REL_DIR="config/stone-prod-p02.hjvn.p1/product/ReleasePlanAdmission/rhdh"
readonly EXPECTED_HTTPS_REMOTE="https://gitlab.cee.redhat.com/releng/konflux-release-data.git"
readonly EXPECTED_SSH_REMOTE="git@gitlab.cee.redhat.com:releng/konflux-release-data.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
readonly SCRIPT_DIR

DRY_RUN=0
VALIDATE=0

usage() {
    cat <<'EOF'
Update RHDH ReleasePlanAdmission tags for a stream release in konflux-release-data.

Usage:
  update-rpa-tags.sh VERSION [OPTIONS]

Arguments:
  VERSION                 Target RHDH version (e.g. 1.9.7, 1.10.3)

Options:
  --repo-dir PATH         konflux-release-data checkout (default: $PWD)
  --dry-run               Preview tag changes without writing, committing, pushing, or opening an MR
  --local-only            Edit the working tree only (also the default); never commit, push, or open an MR
  --validate              Run `tox -e test` after editing (requires tox in repo)
  -h, --help              Show this help

Runtime:
  Bash 3.2+, Git 2.x, and Python 3.9+. The script uses no GNU-only sed, grep,
  or sort behavior.

Examples:
  cd /path/to/konflux-release-data && update-rpa-tags.sh 1.9.7
  update-rpa-tags.sh 1.9.7 --repo-dir /path/to/konflux-release-data
  update-rpa-tags.sh 1.10.3 --dry-run
EOF
}

die() {
    echo "[ERROR] $*" >&2
    exit 1
}

log() {
    echo "[INFO] $*" >&2
}

validate_version() {
    local version="$1"
    [[ "${version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
        || die "Invalid version '${version}'. Expected MAJOR.MINOR.PATCH (e.g. 1.9.7)"
}

version_stream() {
    local version="$1"
    echo "${version%.*}"
}

version_stream_dashed() {
    local stream
    stream=$(version_stream "$1")
    echo "${stream//./-}"
}

resolve_paths() {
    local input="${REPO_DIR:-${KONFLUX_RELEASE_DATA_REPO:-${PWD}}}"
    local git_root
    local canonical_rpa

    [[ -d "${input}" ]] || die "Directory not found: ${input}"
    input=$(cd "${input}" && pwd -P)
    git_root=$(git -C "${input}" rev-parse --show-toplevel 2>/dev/null) \
        || die "Directory is not inside a git repository: ${input}"
    git_root=$(cd "${git_root}" && pwd -P)
    canonical_rpa="${git_root}/${RPA_REL_DIR}"

    if [[ "${input}" != "${git_root}" && "${input}" != "${canonical_rpa}" ]]; then
        die "Use the konflux-release-data root or its canonical RPA directory: ${canonical_rpa}"
    fi
    [[ -d "${canonical_rpa}" ]] \
        || die "Canonical RPA directory not found: ${canonical_rpa}"

    REPO_DIR="${git_root}"
    RPA_DIR="${canonical_rpa}"
    log "Using repository: ${REPO_DIR}"
    log "Using canonical RPA directory: ${RPA_DIR}"
}

collect_target_files() {
    local stream_dashed="$1"
    local file

    TARGET_FILES=(
        "${RPA_DIR}/rhdh-${stream_dashed}-prod.yaml"
        "${RPA_DIR}/rhdh-${stream_dashed}-stage.yaml"
        "${RPA_DIR}/rhdh-plugin-catalog-${stream_dashed}-prod.yaml"
        "${RPA_DIR}/rhdh-plugin-catalog-${stream_dashed}-stage.yaml"
    )
    for file in "${TARGET_FILES[@]}"; do
        [[ -f "${file}" ]] || die "Expected RPA file not found: ${file}"
    done
}

ensure_repository_identity() {
    local url

    url=$(git -C "${REPO_DIR}" remote get-url origin 2>/dev/null) \
        || die "origin is missing. Expected ${EXPECTED_HTTPS_REMOTE}"
    case "${url}" in
        "${EXPECTED_HTTPS_REMOTE}" | "${EXPECTED_HTTPS_REMOTE%.git}" | \
        "${EXPECTED_SSH_REMOTE}" | "${EXPECTED_SSH_REMOTE%.git}" | \
        "ssh://git@gitlab.cee.redhat.com/releng/konflux-release-data.git" | \
        "ssh://git@gitlab.cee.redhat.com/releng/konflux-release-data")
            ;;
        *)
            die "origin identifies '${url}', not releng/konflux-release-data on gitlab.cee.redhat.com"
            ;;
    esac
}

ensure_clean_checkout() {
    local status

    status=$(git -C "${REPO_DIR}" status --porcelain --untracked-files=all)
    [[ -z "${status}" ]] \
        || die "Repository has tracked or untracked changes. Commit, stash, or remove them before editing."
}

run_updater() {
    local args=(--stream "${STREAM}" --to "${NEW_VERSION}")
    local report

    if [[ ${DRY_RUN} -eq 0 ]]; then
        args+=(--write)
    fi
    if ! report=$(python3 "${SCRIPT_DIR}/update_rpa_tags.py" \
        "${args[@]}" --rpa-dir "${RPA_DIR}" "${TARGET_FILES[@]}"); then
        die "The tag update failed; no publish operation was attempted."
    fi
    printf '%s\n' "${report}"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -h | --help)
            usage
            exit 0
            ;;
        --repo-dir)
            [[ $# -ge 2 ]] || die "--repo-dir requires a path"
            REPO_DIR=$2
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --local-only)
            shift
            ;;
        --validate)
            VALIDATE=1
            shift
            ;;
        -*)
            die "Unknown option: $1"
            ;;
        *)
            if [[ -z "${NEW_VERSION}" ]]; then
                NEW_VERSION=$1
            else
                die "Unexpected argument: $1"
            fi
            shift
            ;;
    esac
done

[[ -n "${NEW_VERSION}" ]] || {
    usage
    exit 1
}

validate_version "${NEW_VERSION}"
resolve_paths

STREAM=$(version_stream "${NEW_VERSION}")
STREAM_DASHED=$(version_stream_dashed "${NEW_VERSION}")
declare -a TARGET_FILES
collect_target_files "${STREAM_DASHED}"

if [[ ${DRY_RUN} -eq 1 ]]; then
    run_updater
    log "Dry run complete; the checkout is unchanged"
    exit 0
fi

ensure_repository_identity
ensure_clean_checkout
run_updater

if [[ ${VALIDATE} -eq 1 ]]; then
    command -v tox >/dev/null 2>&1 || die "--validate requires tox on PATH"
    log "Running tox -e test"
    (cd "${REPO_DIR}" && tox -e test)
fi

log "Local-only update complete; nothing was staged, committed, pushed, or opened"
