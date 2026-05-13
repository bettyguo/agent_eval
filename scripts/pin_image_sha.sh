#!/usr/bin/env bash
# Resolve the pinned sandbox base image to a SHA256 digest and update
# sandbox/image.lock in place. Run when the base image is bumped.
#
# Requires: Docker daemon running, jq.
#
# Usage:
#   ./scripts/pin_image_sha.sh                          # use the tag in image.lock
#   ./scripts/pin_image_sha.sh python:3.11-bookworm-slim  # override

set -euo pipefail

LOCK_FILE="sandbox/image.lock"

if [[ ! -f "$LOCK_FILE" ]]; then
    echo "error: $LOCK_FILE not found (run from repo root)" >&2
    exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
    echo "error: jq is required" >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "error: docker is required" >&2
    exit 1
fi

TAG="${1:-$(jq -r '.image' "$LOCK_FILE")}"
echo "Pulling $TAG ..."
docker pull "$TAG"

DIGEST=$(docker inspect --format='{{index .RepoDigests 0}}' "$TAG" | awk -F'@' '{print $2}')
if [[ -z "$DIGEST" || "$DIGEST" != sha256:* ]]; then
    echo "error: could not resolve digest for $TAG" >&2
    exit 2
fi

TODAY=$(date -u +"%Y-%m-%d")

tmp=$(mktemp)
jq \
    --arg img "$TAG" \
    --arg sha "$DIGEST" \
    --arg today "$TODAY" \
    '.image = $img | .sha256 = $sha | .last_audited = $today' \
    "$LOCK_FILE" > "$tmp"
mv "$tmp" "$LOCK_FILE"

echo
echo "Updated $LOCK_FILE:"
echo "  image:       $TAG"
echo "  sha256:      $DIGEST"
echo "  last_audited: $TODAY"
echo
echo "Commit the change and re-run leaderboard verification afterward.
The sandbox image SHA is stored on each entry but not hashed; mismatch on
re-verification fires the sandbox-drift flag."
