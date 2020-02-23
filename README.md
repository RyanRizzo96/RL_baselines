

# Baselines

RLBaselines is built upon [OpenAI Baselines](https://github.com/openai/baselines) and uses improved documentation and code quality from Stable Baselines. Follow OpenAI's installation guide to get started.

# Improved Plotting

1. Added [tensorboard-aggregator](https://github.com/Spenhouet/tensorboard-aggregator) to aggregate multiple tensorboard runs.
2. Added `csv_aggregator.py` for easier and more intuitive plotting of mean and standard deviation.

The shaded blue is the standard deviation from the mean, while the orange shade is the error in estimate of the mean. 

![image](https://user-images.githubusercontent.com/31866965/74467100-bd87a380-4e98-11ea-930e-0ca0b5bead7d.png)

3. Added `csv_plot.py` to improve ease of use in utilising baseline plotting functions.

![image](https://user-images.githubusercontent.com/31866965/74468656-75b64b80-4e9b-11ea-8ff4-2755eb7aee26.png)


# Results

![image](https://user-images.githubusercontent.com/31866965/75112455-4eead880-5644-11ea-9bd9-76bc80de7fd9.png)

# Road map

- [ ] Plot results using seaborn 
- [ ] Compare results in a more professional manner
- [ ] Implement Prioritzied Sequence Experience Replay
- [ ] Implement Energy Based Prioritization
- [ ] Compare the above
