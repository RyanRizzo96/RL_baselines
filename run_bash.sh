#!/usr/bin/env bash
source ~/.virtualenvs/baseline_env/bin/activate

echo $HOME
echo $PWD

export OPENAI_LOGDIR=.log/HER5k_trial/test4
export OPENAI_LOG_FORMAT=stdout,log,csv,tensorboard

#tensorboard --logdir ./a2c_cartpole_tensorboard/ --host localhost --port 8088

#Use --env not env for HER. Seems like for other algs this is not the same
#python3 -m baselines.run --alg=her env=FetchReach-v1 --num_timesteps=1e5
python3 -m baselines.run --alg=her --env=FetchReach-v1 --num_timesteps=10000 --save_path=.models/FetchReach_10k_her --play
#python3 -m baselines.run --alg=deepq --env=CartPole-v0 --print_freq=1 --num_timesteps=1e4

python3 csv_plot.py