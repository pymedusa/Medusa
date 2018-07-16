#!/bin/bash
set -ev

cd themes-default/slim/
yarn gulp sync
cd ../../
status="$(git status --porcelain -- themes/)";
if [[ -n $status ]]; then
    echo "Please build the themes"
    echo "-----------------------"
    echo "$status"
    exit 1
fi