#!/usr/bin/env bash
source ~/.virtualenvs/baseline_env/bin/activate

echo $HOME
echo $PWD

export OPENAI_LOGDIR=.log/HER
export OPENAI_LOG_FORMAT=stdout,log,csv,tensorboard

#tensorboard --logdir ./a2c_cartpole_tensorboard/ --host localhost --port 8088

#Use --env not env for HER. Seems like for other algs this is not the same
#python3 -m baselines.run --alg=her env=FetchReach-v1 --num_timesteps=1e5
python3 -m baselines.run --alg=her --env=FetchReach-v1 --num_timesteps=5000