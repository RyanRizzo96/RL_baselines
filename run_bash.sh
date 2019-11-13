#!/usr/bin/env bash
source ~/.virtualenvs/baseline_env/bin/activate

# echo $HOME
# echo $PWD

export OPENAI_LOG_FORMAT=stdout,log,csv,tensorboard

python3 -m baselines.run --alg=her --env=FetchReach-v1  --num_timesteps=5000

#coverage run -m baselines.run --alg=her --env=FetchReach-v1  --num_timesteps=5000
#coverage report -m -i
#coverage html -i

# python3 -m baselines.run --alg=her --env=FetchPush-v1 --num_timesteps=0 --load_path=/Users/ryanr/B.Eng/MCAST_Degree_4/Thesis/code/baseline_code/baselines/policies/her/FPUSH_200k/standard --play

# for seed in $(seq 0 5); do OPENAI_LOGDIR=$HOME/logs/her_seed/run1-$seed python3 -m baselines.run --alg=her --env=FetchReach-v1 --num_timesteps=5000 --seed=$seed --nsteps=32; done



# TEST 2
# mpirun -np 19 python3 -m baselines.run --alg=her --env=FetchPickAndPlace-v1  --num_timesteps=1000000 --save_path=.models/her/FPAP_1mil_run3

# mpirun -np 19 python3 -m baselines.run --alg=her --env=FetchPickAndPlace-v1  --num_timesteps=1000 --save_path=.models/her/ec2_test_5k_test

# mpirun -np 19 python3 -m baselines.run --alg=her --env=FetchSlide-v1 --num_timesteps=200000 --save_path=policies/her/FSLIDE_200k/standard

# python3 csv_plot.py
