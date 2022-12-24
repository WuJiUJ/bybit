#!/bin/sh
cd /home/wuji/bot/bybit

git add *
timestamp(){"%d.%m.%Y um %H:%M"}
git commit -am "Auto Server Commit $(timestamp)"
git push