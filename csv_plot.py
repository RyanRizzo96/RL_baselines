from baselines.common import plot_util as plot
import matplotlib.pyplot as plt
import numpy as np

results = plot.load_results('.log/DEEPQ5k')  # pass variable from bash script
print(results)
r = results[0]
plt.plot(np.cumsum(r.monitor.l), plot.smooth(r.monitor.r, radius=1))  # radius to smoother
plt.xlabel('Steps')
plt.ylabel('Reward')
plt.show()
