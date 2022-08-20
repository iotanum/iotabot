#!/bin/bash

NAME=osu
REPO_URI=https://github.com/ppy/osu
RULESETS_ARRAY=(
"osu.Game.Rulesets.Catch"
"osu.Game.Rulesets.Mania"
"osu.Game.Rulesets.Osu"
"osu.Game.Rulesets.Taiko"
"osu.Game"
)

mkdir $NAME
cd $NAME || exit 1
git init
git remote add origin $REPO_URI
git config core.sparseCheckout true

# Add which rulesets we want (taken from useLocalOsu.sh in osu-tools repo)
for ruleset in ${RULESETS_ARRAY[*]}; do
    echo "$ruleset" >> .git/info/sparse-checkout
done

git pull --depth=1 origin master
