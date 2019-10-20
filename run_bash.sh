#!/usr/bin/env bash
source ~/.virtualenvs/baseline_env/bin/activate

# echo $HOME
# echo $PWD

# export OPENAI_LOGDIR=.log/FetchReach/HER5k/trial1
export OPENAI_LOG_FORMAT=stdout,log,csv,tensorboard

python3 -m baselines.run --alg=her --env=FetchReach-v1 --num_timesteps=5000 --save_path=.models/FetchReach/5k_512_hidden

# python3 csv_plot.py
