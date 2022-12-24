class Statistic:
    def __init__(self, total_usdt):
        self.portfolio_value = None
        self.total_usdt_balance = total_usdt

    def __str__(self):
        return "Statistic: " + str(self.__dict__)
