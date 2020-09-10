#!/bin/bash
set -e

# This script expects to be run in: `Medusa/themes-default/slim`
path_to_built_themes="../../themes/"

# Helper function to print the command before running it.
run_verbose () {
    echo "\$ $*"
    eval $*
}

get_size () {
    du -sb $1 | cut -f1
}

# Determine if and how to build the Webpack bundle.
build_cmd=""
build_mode=""
# $TRAVIS_BRANCH is either a PR's target branch, or the current branch if it's a push build.
# Do not build on other branches because it will cause conflicts on pull requests,
#   where push builds build for development and PR builds build for production.
if [[ $TRAVIS_BRANCH == "master" ]]; then
    build_cmd="yarn build"
    build_mode="production"
elif [[ $TRAVIS_BRANCH == "develop" ]]; then
    build_cmd="yarn dev"
    build_mode="development"
fi

# Keep track of the current themes size.
size_before=$(get_size $path_to_built_themes)

# Build themes.
[[ -n $build_cmd ]] && run_verbose "$build_cmd"
run_verbose "yarn gulp sync"

# Normalize line endings in changed files
changed_files=$(git status --porcelain -- $path_to_built_themes | sed s/^...//)
for file in $changed_files; do
    sed -i 's/\r$//g' ../../$file;
done

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
