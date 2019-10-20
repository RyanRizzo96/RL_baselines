from baselines.common import plot_util as plot
import matplotlib.pyplot as plt
import numpy as np
import os

# osprint(os.environ['OPENAI_LOGDIR'])

OPENAI_LOGDIR=".log/FetchReach/HER5k/trial1"

results = plot.load_results(OPENAI_LOGDIR)  # pass variable from bash script
print(results)
r = results[0]
plt.plot(np.cumsum(r.monitor.l), plot.smooth(r.monitor.r, radius=1))  # radius to smoother
plt.xlabel('Episodes')
plt.ylabel('Reward')
plt.show()
