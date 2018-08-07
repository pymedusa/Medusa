#!/bin/bash
set -e

run_verbose () {
    echo "\$ $*"
    eval $*
}

# $TRAVIS_BRANCH is either a PR's target branch, or the current branch if it's a push build.
if [[ $TRAVIS_BRANCH == "master" ]]; then
    build_cmd="webpack-build"
    build_mode="production"
else
    build_cmd="dev"
    build_mode="development"
fi

cd themes-default/slim/
run_verbose "yarn $build_cmd"
run_verbose "yarn gulp sync"
cd ../../

status_cmd="git status --porcelain -- themes/"

# if [[ $build_mode == "development" ]]; then
#     status_cmd="$status_cmd :(exclude)themes/*/assets/js/vendors.js"
# fi

status="$($status_cmd)";
if [[ -n $status ]]; then
    echo "Please build the themes (mode: $build_mode) "
    echo "--------------------------------------------"
    echo "$status"
    exit 1
fi
