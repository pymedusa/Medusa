#!/bin/bash
set -e

# This script expects to be run in: `Medusa/themes-default/slim`
path_to_built_themes="../../themes/"

python_cmd="python3"
command -v python3 >/dev/null 2>&1 || python_cmd="python"

# Helper function to print the command before running it.
run_verbose () {
    echo "\$ $*"
    eval $*
}

get_size () {
    local path="$1"
    local size

    # Prefer GNU `du -sb` when available (Linux), but fall back to a portable
    # byte-accurate implementation (macOS/BSD `du` lacks `-b`).
    if size="$(du -sb "$path" 2>/dev/null | cut -f1)"; then
        echo "$size"
        return 0
    fi

    "$python_cmd" - "$path" <<'PY'
import os
import sys

root = sys.argv[1]
total = 0

def safe_lstat_size(path: str) -> int:
    try:
        return os.lstat(path).st_size
    except OSError:
        # If a file disappears between walk/stat, skip it.
        return 0

for dirpath, dirnames, filenames in os.walk(root):
    total += safe_lstat_size(dirpath)

    for dirname in dirnames:
        total += safe_lstat_size(os.path.join(dirpath, dirname))

    for filename in filenames:
        total += safe_lstat_size(os.path.join(dirpath, filename))

print(total)
PY
}

# Determine if and how to build the Webpack bundle.
build_cmd=""
build_mode=""
# ${GITHUB_BASE_REF##*/} is a PR's target branch.
# Do not build on other branches because it will cause conflicts on pull requests,
# where push builds build for development and PR builds build for production.
if [[ ${GITHUB_BASE_REF##*/} == "master" ]]; then
    build_cmd="yarn build"
    build_mode="production"
elif [[ ${GITHUB_BASE_REF##*/} == "develop" ]]; then
    build_cmd="yarn dev"
    build_mode="development"
fi

# Keep track of the current themes size.
size_before=$(get_size $path_to_built_themes)

# Build themes.
[[ -n $build_cmd ]] && run_verbose "$build_cmd"
run_verbose "yarn gulp sync"

# Normalize line endings in changed files (portable across GNU/BSD sed)
# Use `git status -z` to safely handle filenames with whitespace.
while IFS= read -r -d '' entry; do
    [[ -z $entry ]] && continue

    status="${entry:0:2}"
    file="${entry:3}"

    # For rename/copy, porcelain `-z` provides two paths: "old\0new\0".
    if [[ $status == *R* || $status == *C* ]]; then
        IFS= read -r -d '' file || true
    fi

    [[ -n $file && -f ../../"$file" ]] || continue

    "$python_cmd" - ../../"$file" <<'PY'
import re
import sys

path = sys.argv[1]
with open(path, "rb") as f:
    data = f.read()

new_data = re.sub(br"\r(?=\n|$)", b"", data)
if new_data != data:
    with open(path, "wb") as f:
        f.write(new_data)
PY
done < <(git status --porcelain -z -- "$path_to_built_themes")

# Keep track of the new themes size.
size_after=$(get_size $path_to_built_themes)

echo "Themes size before: $size_before"
echo "Themes size after: $size_after"

# Check if the themes changed.
status="$(git status --porcelain -- $path_to_built_themes)";
if [[ -n $status && $size_before != $size_after ]]; then
    if [[ -z $build_mode ]]; then
        echo "Please build the themes"
        echo "-----------------------"
    else
        echo "Please build the themes (mode: $build_mode) "
        echo "--------------------------------------------"
    fi
    echo "$status"
    exit 1
fi
