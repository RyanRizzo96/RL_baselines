#!/usr/bin/env bash
source ~/.virtualenvs/baseline_env/bin/activate

echo $HOME
echo $PWD

export OPENAI_LOGDIR=.log
export OPENAI_LOG_FORMAT=stdout,log,csv,tensorboard

python3 -m baselines.run --alg=deepq --env=CartPole-v0 --print_freq=1 --num_timesteps=1e5