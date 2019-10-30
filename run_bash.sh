#!/usr/bin/env bash
source ~/.virtualenvs/baseline_env/bin/activate

# echo $HOME
# echo $PWD

# export OPENAI_LOGDIR=.log/FetchReach/HER5k/trial1
# export OPENAI_LOG_FORMAT=stdout,log,csv,tensorboard

export OPENAI_LOG_FORMAT=csv

# python3 -m baselines.run --alg=her --env=FetchReach-v1 --num_timesteps=5000 --save_path=.models/FetchReach/3_layers

# mpirun -np 19 python3 -m baselines.run --alg=her --env=FetchPickAndPlace-v1 --env=FetchPush-v1 --num_timesteps=10000 --save_path=~/policies/her/run4/10k

# mpirun -np 19 python3 -m baselines.run --alg=her --env=FetchPickAndPlace-v1  --num_timesteps=1000000 --save_path=./models/her/run5/FPAP_1mil

# python3 -m baselines.run --alg=her --env=FetchPickAndPlace-v1 --num_timesteps=0 --load_path=/Users/ryanr/B.Eng/MCAST_Degree_4/Thesis/code/baseline_code/baselines/.models/her/ec2_test_5k_test --play

# python3 -m baselines.run --alg=her --env=FetchReach-v1 --num_timesteps=1000

# for seed in $(seq 0 5); do OPENAI_LOG_FORMAT=csv OPENAI_LOGDIR=$HOME/logs/her_seed/b32-$seed python3 -m baselines.run --alg=her --env=FetchReach-v1 --num_timesteps=10000 --seed=$seed --nsteps=32; done

# TEST 2
mpirun -np 19 python3 -m baselines.run --alg=her --env=FetchPickAndPlace-v1  --num_timesteps=1000000 --save_path=.models/her/FPAP_1mil_run2

# mpirun -np 19 python3 -m baselines.run --alg=her --env=FetchPickAndPlace-v1  --num_timesteps=1000 --save_path=.models/her/ec2_test_5k_test

# mpirun -np 19 python3 -m baselines.run --num_env=2 --alg=her --env=FetcPickAndPlace-v1 --env=FetchPush-v1 --num_timesteps=2000000 --save_path=~/policies/her/run1/2mil

# python3 csv_plot.py
