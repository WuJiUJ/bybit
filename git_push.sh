#!/bin/sh

export GIT_SSH_COMMAND="ssh -i /home/wuji/.ssh/id_ed25519"

cd /home/wuji/bot/bybit

git add .
git commit -m "Auto Server Commit"
git push