#!/usr/bin/env bash
source ~/.virtualenvs/baseline_env/bin/activate

echo $HOME
echo $PWD

export OPENAI_LOGDIR=.log/FetchReach/HER5k/trial1
export OPENAI_LOG_FORMAT=stdout,log,csv,tensorboard

python3 -m baselines.run --alg=her --env=FetchReach-v1 --num_timesteps=5000 --save_path=.models/FetchReach_5k_her
#python3 -m baselines.run --alg=deepq --env=CartPole-v0 --print_freq=1 --num_timesteps=1e4

python3 csv_plot.py