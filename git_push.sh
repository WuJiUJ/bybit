#!/bin/sh

USERNAME="WuJiUJ"
PASSWORD="Wuji.!2000"
REMOTE_REPO="github.com/WuJiUJ/bybit.git"
EMAIL="email@domain.com"

cd /home/wuji/bot/bybit

git add *
git commit -m "Auto Server Commit"
git push -u https://$USERNAME:$PASSWORD@$REMOTE_REPO main >> ./logs/git_log.log