#!/usr/bin/env bash
source ~/.virtualenvs/baseline_env/bin/activate

# echo $HOME
# echo $PWD

# export OPENAI_LOGDIR=.log/FetchReach/HER5k/trial1
export OPENAI_LOG_FORMAT=stdout,log,csv,tensorboard

python3 -m baselines.run --alg=her --env=FetchReach-v1 --num_timesteps=5000 --save_path=.models/FetchReach/3_layers

python3 mpirun -np 19 python -m baselines.run --num_env=2 --alg=her --env=FetcPickAndPlace-v1 --env=FetchPush-v1 --num_timesteps=2000000 --save_path=~/policies/her/run1/2mil

# python3 csv_plot.py
