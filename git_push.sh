#!/bin/sh

USERNAME="WuJiUJ"
PASSWORD="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"
REMOTE_REPO="github.com/WuJiUJ/bybit.git"
EMAIL="email@domain.com"

cd /home/wuji/bot/bybit

git add -u
git commit -m "Auto Server Commit"
git push -u https://$USERNAME:$PASSWORD@$REMOTE_REPO main >> ./logs/git_log.log