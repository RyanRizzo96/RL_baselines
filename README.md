

# Baselines

RLBaselines is built upon [OpenAI Baselines](https://github.com/openai/baselines) and uses improved documentation and code quality from Stable Baselines. Follow OpenAI's installation guide to get started.

# Improved Plotting

1. Added [tensorboard-aggregator](https://github.com/Spenhouet/tensorboard-aggregator) to aggregate multiple tensorboard runs.
2. Added `csv_aggregator.py` for easier and more intuitive plotting of mean and standard deviation.

The shaded blue is the standard deviation from the mean, while the orange shade is the error in estimate of the mean. 

![image](https://user-images.githubusercontent.com/31866965/74467100-bd87a380-4e98-11ea-930e-0ca0b5bead7d.png)

3. Added `csv_plot.py` to improve ease of use in utilising baseline plotting functions.

![image](https://user-images.githubusercontent.com/31866965/74468656-75b64b80-4e9b-11ea-8ff4-2755eb7aee26.png)


# Why are results outperforming original baselines results? 

- Results are obtained 50 times faster in certain environments. Where is the flaw in my plotting or calculations? Anyone who can point this out, kindly open an issue. Greatly apprciated!

![image](https://user-images.githubusercontent.com/31866965/74676409-444cc100-51b6-11ea-93b8-2a9530ad4df2.png)
