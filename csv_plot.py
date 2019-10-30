from baselines.common import plot_util as plot
from baselines.common import plot_util as pu
import matplotlib.pyplot as plt
import numpy as np
import os

# osprint(os.environ['OPENAI_LOGDIR'])

# OPENAI_LOGDIR=".log/FetchReach/HER5k/trial1"

# results = plot.load_results(".log/HER/test_5k/2019-10-27-13-52-48")  # pass variable from bash script
# print(results)
# r = results[0]
# plt.plot(np.cumsum(r.monitor.l), plot.smooth(r.monitor.r, radius=1))  # radius to smoother
# print(r.monitor.l)
# plt.xlabel('Episodes')
# plt.ylabel('Reward')
# plt.show()


# Plotting with random seeds

results = pu.load_results('~/logs/her_seed')
print(len(results))
pu.plot_results(results)
pu.plot_results(results, average_group=True)
plt.show()
