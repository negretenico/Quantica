#!/usr/bin/env bash
set -euo pipefail

BUMP_TYPE="${1:-}"
if [[ "$BUMP_TYPE" != "patch" && "$BUMP_TYPE" != "minor" && "$BUMP_TYPE" != "major" ]]; then
  echo "Usage: ./bump.sh patch|minor|major"
  exit 1
fi

# Read current version from pom.xml (source of truth), strip -SNAPSHOT if present
CURRENT=$(cd marketListener && mvn help:evaluate -Dexpression=project.version -q -DforceStdout | sed 's/-SNAPSHOT//')

IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$BUMP_TYPE" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
esac

NEW="$MAJOR.$MINOR.$PATCH"
JAVA_VERSION="${NEW}-SNAPSHOT"
PYTHON_VERSION="${NEW}.dev0"

echo "Bumping $CURRENT → $NEW"

# Java: use Maven versions plugin (handles pom.xml correctly)
for module in marketListener markettransformer; do
  (cd "$module" && mvn versions:set -DnewVersion="$JAVA_VERSION" -DgenerateBackupPoms=false -q)
done

# Python: replace version line in pyproject.toml
for module in marketanalysis marketbard; do
  sed -i "s/^version = .*/version = \"${PYTHON_VERSION}\"/" "$module/pyproject.toml"
done

echo ""
echo "Done."
echo "  Java:   $JAVA_VERSION  (marketListener, markettransformer)"
echo "  Python: $PYTHON_VERSION  (marketanalysis, marketbard)"
