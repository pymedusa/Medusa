#!/bin/bash
set -e

run_verbose () {
   echo "\$ $*"
   eval $*
}

cd themes-default/slim/
run_verbose "yarn webpack-build"
run_verbose "yarn gulp sync"
cd ../../
status="$(git status --porcelain -- themes/)";
if [[ -n $status ]]; then
    echo "Please build the themes"
    echo "-----------------------"
    echo "$status"
    exit 1
fi