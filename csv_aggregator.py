import numpy as np
import os
import pandas as pd
import matplotlib.pyplot as plt
import csv

headers = ['Mean', 'aMin', 'aMax', 'Median', 'std', 'var']
df = pd.read_csv(
    '/Users/ryanr/B.Eng/MCAST_Degree_4/Thesis/code/gym/RL_baselines/.log/run_1/testing_structure/aggregates/stats_gmean-tb-testing_structure.csv',
    sep=',',  dtype=float)

# Preview the first 5 lines of the loaded data
print(df.head(10))

count_row = df.shape[0]  # gives number of row count
count_col = df.shape[1]  # gives number of col count

print("rows", count_row)
print("cols", count_col)
# print(df.iloc[:,0])

# plt.plot(df[])

# First three columns to obtain mean, min and max
for i in range(1, 4):
    plt.plot(df.iloc[:,0], df.iloc[:,i], label='id %s' %i)

plt.legend()
plt.show()
