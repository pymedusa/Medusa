#!/bin/bash
set -e

# Helper function to print the command before running it.
run_verbose () {
    echo "\$ $*"
    eval $*
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

# Keep track of the current themes sizes.
size_before=$(du -sb themes/ | cut -f1)
echo "Size before: $size_before"

# Build themes.
cd themes-default/slim/
[[ -n $build_cmd ]] && run_verbose "$build_cmd"
run_verbose "yarn gulp sync"
cd ../../

# Keep track of the new themes sizes.
size_after=$(du -sb themes/ | cut -f1)
echo "Size after: $size_after"

# Check if the themes changed.
status="$(git status --porcelain -- themes/)";
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
