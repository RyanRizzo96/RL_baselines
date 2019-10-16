from baselines.common import plot_util as plot
import matplotlib.pyplot as plt
import numpy as np

results = plot.load_results('~/logs/HER')
print(results)
r = results[0]
plt.plot(np.cumsum(r.monitor.l), plot.smooth(r.monitor.r, radius=10))  # radius to smoother
plt.xlabel('Iterations')
plt.ylabel('Reward')
plt.show()
