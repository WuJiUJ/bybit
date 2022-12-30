import pandas as pd

df = pd.DataFrame(data={"signal": [True, True], "initial": [0.2, 0.3]})
df1 = {}

print(df.iloc[0].to_dict())
# print(df1["signal"])
