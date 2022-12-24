import os
import pandas as pd

class Logger:
    def to_csv(info_type, data):  # no need for self since static method
        try:
            filename = f"logs/{info_type}_logs.csv"
            df = pd.DataFrame(data=data.__dict__, index=[0])
            if os.path.exists(filename):
                prev_df = pd.read_csv(filename, sep="?")
                df = pd.concat([prev_df, df])
            df.to_csv(filename, index=False, sep="?")
        except Exception as e:
            print(f"Logging Error: ", e)


# create addNumbers static method
Logger.to_csv = staticmethod(Logger.to_csv)
