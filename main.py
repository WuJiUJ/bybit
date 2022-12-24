from bot import Bot


def main():
    bot = Bot(60)  # 1260
    bot.run("start")
    # bot.run_loop()


# PATH=/home/wuji/miniconda3/envs/py310/bin
# PYTHONPATH=/home/wuji/bot/bybit
# 58 7,15,23 * * * /home/wuji/bot/bybit/cron.sh >> /home/wuji/bot/bybit/logs/clogs.log 2>&1

if __name__ == "__main__":
    main()
