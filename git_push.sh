#!/bin/sh

USERNAME="WuJiUJ"
PASSWORD="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"
REMOTE_REPO="github.com/WuJiUJ/bybit.git"
EMAIL="email@domain.com"

cd /home/wuji/bot/bybit

git add -u
git commit -m "Auto Server Commit"
git push -u https://$USERNAME:$PASSWORD@$REMOTE_REPO main >> ./logs/git_log.log