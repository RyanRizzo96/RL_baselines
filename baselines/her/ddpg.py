from collections import OrderedDict

import numpy as np
import tensorflow as tf
from tensorflow.contrib.staging import StagingArea

from baselines import logger
from baselines.her.util import (
    import_function, store_args, flatten_grads, transitions_in_episode_batch, convert_episode_to_batch_major)
from baselines.her.normalizer import Normalizer
from baselines.her.replay_buffer import ReplayBuffer
from baselines.common.mpi_adam import MpiAdam
from baselines.common import tf_util


def dims_to_shapes(input_dims):
    return {key: tuple([val]) if val > 0 else tuple() for key, val in input_dims.items()}


global DEMO_BUFFER #buffer for demonstrations


class DDPG(object):
    @store_args
    def __init__(self, input_dims, buffer_size, hidden, layers, network_class, polyak, batch_size,
                 Q_lr, pi_lr, norm_eps, norm_clip, action_scale, action_l2, clip_obs, scope, T,
                 rollout_batch_size, subtract_goals, relative_goals, clip_pos_returns, clip_return,
                 bc_loss, q_filter, num_demo, demo_batch_size, prm_loss_weight, aux_loss_weight,
                 sample_transitions, gamma, reuse=False, **kwargs):
        """
            Implementation of DDPG that is used in combination with Hindsight Experience Replay (HER).
            Added functionality to use demonstrations for training to Overcome exploration problem.
        Args:
            :param input_dims (dict of ints): dimensions for the observation (o), the goal (g), and the
                actions (u)
            :param buffer_size (int): number of transitions that are stored in the replay buffer
            :param hidden (int): number of units in the hidden layers
            :param layers (int): number of hidden layers
            :param network_class (str): the network class that should be used (e.g. 'baselines.her.ActorCritic')
            :param polyak (float): coefficient for Polyak-averaging of the target network
            :param batch_size (int): batch size for training
            :param Q_lr (float): learning rate for the Q (critic) network
            :param pi_lr (float): learning rate for the pi (actor) network
            :param norm_eps (float): a small value used in the normalizer to avoid numerical instabilities
            :param norm_clip (float): normalized inputs are clipped to be in [-norm_clip, norm_clip]
            :param action_scale(float): maximum action magnitude, i.e. actions are in [-max_u, max_u]
            :param action_l2 (float): coefficient for L2 penalty on the actions
            :param clip_obs (float): clip observations before normalization to be in [-clip_obs, clip_obs]
            :param scope (str): the scope used for the TensorFlow graph
            :param T (int): the time horizon for rollouts
            :param rollout_batch_size (int): number of parallel rollouts per DDPG agent
            :param subtract_goals (function): function that subtracts goals from each other
            :param relative_goals (boolean): whether or not relative goals should be fed into the network
            :param clip_pos_returns (boolean): whether or not positive returns should be clipped
            :param clip_return (float): clip returns to be in [-clip_return, clip_return]
            :param sample_transitions (function) function that samples from the replay buffer
            :param gamma (float): gamma used for Q learning updates
            :param reuse (boolean): whether or not the networks should be reused
            :param bc_loss: whether or not the behavior cloning loss should be used as an auxilliary loss
            :param q_filter: whether or not a filter on the q value update should be used when training with demonstartions
            :param num_demo: Number of episodes in to be used in the demonstration buffer
            :param demo_batch_size: number of samples to be used from the demonstrations buffer, per mpi thread
            :param prm_loss_weight: Weight corresponding to the primary loss
            :param aux_loss_weight: Weight corresponding to the auxilliary loss also called the cloning loss
        """
        if self.clip_return is None:
            self.clip_return = np.inf

        self.create_actor_critic = import_function(self.network_class)  # points to actor_critic.py

        self.input_dims = input_dims

        input_shapes = dims_to_shapes(input_dims)
        self.dimo = input_dims['o']
        self.dimg = input_dims['g']
        self.dimu = input_dims['u']

        # Prepare staging area for feeding data to the model.
        stage_shapes = OrderedDict()
        for key in sorted(self.input_dims.keys()):
            if key.startswith('info_'):
                continue
            stage_shapes[key] = (None, *input_shapes[key])
        for key in ['o', 'g']:
            stage_shapes[key + '_2'] = stage_shapes[key]
        stage_shapes['r'] = (None,)
        self.stage_shapes = stage_shapes

        # Create network.
        with tf.variable_scope(self.scope):
            self.staging_tf = StagingArea(
                dtypes=[tf.float32 for _ in self.stage_shapes.keys()],
                shapes=list(self.stage_shapes.values()))
            self.buffer_ph_tf = [
                tf.placeholder(tf.float32, shape=shape) for shape in self.stage_shapes.values()]
            self.stage_op = self.staging_tf.put(self.buffer_ph_tf)

            self._create_network(reuse=reuse)  # Creates DDPG agent

        # Configure the replay buffer.
        buffer_shapes = {key: (self.T-1 if key != 'o' else self.T, *input_shapes[key])
                         for key, val in input_shapes.items()}
        buffer_shapes['g'] = (buffer_shapes['g'][0], self.dimg)
        buffer_shapes['ag'] = (self.T, self.dimg)

        buffer_size = (self.buffer_size // self.rollout_batch_size) * self.rollout_batch_size
        self.buffer = ReplayBuffer(buffer_shapes, buffer_size, self.T, self.sample_transitions)

        global DEMO_BUFFER
        # initialize the demo buffer; in the same way as the primary data buffer
        DEMO_BUFFER = ReplayBuffer(buffer_shapes, buffer_size, self.T, self.sample_transitions)

    def _random_action(self, n):
        return np.random.uniform(low=-self.action_scale, high=self.action_scale, size=(n, self.dimu))

    def _preprocess_og(self, o, ag, g):
        if self.relative_goals:  # no self.relative_goals
            print("self.relative_goals: ", self.relative_goals)
            g_shape = g.shape
            g = g.reshape(-1, self.dimg)
            ag = ag.reshape(-1, self.dimg)
            g = self.subtract_goals(g, ag)
            g = g.reshape(*g_shape)

        # Clip (limit) the values in an array.
        o = np.clip(o, -self.clip_obs, self.clip_obs)
        g = np.clip(g, -self.clip_obs, self.clip_obs)

        return o, g

    # Not used
    def step(self, obs):
        actions = self.get_actions(obs['observation'], obs['achieved_goal'], obs['desired_goal'])
        return actions, None, None, None

    def get_actions(self, o, ag, g, noise_eps=0., random_eps=0., use_target_net=False,
                    compute_Q=False):

        o, g = self._preprocess_og(o, ag, g)

        # Use target network use main network
        policy = self.target if use_target_net else self.main

        # values to compute
        policy_weights = [policy.actor_tf]
        if compute_Q:
            policy_weights += [policy.critic_with_actor_tf]

        # feed
        agent_feed = {
            policy.obs: o.reshape(-1, self.dimo),
            policy.goals: g.reshape(-1, self.dimg),
            policy.actions: np.zeros((o.size // self.dimo, self.dimu), dtype=np.float32)
        }

        # Evaluating policy weights with agent information
        ret = self.sess.run(policy_weights, feed_dict=agent_feed)

        # print(ret)

        # action postprocessing
        action = ret[0]
        noise = noise_eps * self.action_scale * np.random.randn(*action.shape)  # gaussian noise
        action += noise
        action = np.clip(action, -self.action_scale, self.action_scale)
        action += np.random.binomial(1, random_eps, action.shape[0]).reshape(-1, 1) * (self._random_action(action.shape[0]) - action)  # eps-greedy
        if action.shape[0] == 1:
            action = action[0]
        action = action.copy()
        ret[0] = action

        if len(ret) == 1:
            return ret[0]
        else:
            return ret

    # Not used
    def init_demo_buffer(self, demoDataFile, update_stats=True):  # function that initializes the demo buffer

        demoData = np.load(demoDataFile)  # load the demonstration data from data file
        info_keys = [key.replace('info_', '') for key in self.input_dims.keys() if key.startswith('info_')]
        info_values = [np.empty((self.T - 1, 1, self.input_dims['info_' + key]), np.float32) for key in info_keys]

        demo_data_obs = demoData['obs']
        demo_data_acs = demoData['acs']
        demo_data_info = demoData['info']

        for epsd in range(self.num_demo): # we initialize the whole demo buffer at the start of the training
            obs, acts, goals, achieved_goals = [], [] ,[] ,[]
            i = 0
            for transition in range(self.T - 1):
                obs.append([demo_data_obs[epsd][transition].get('observation')])
                acts.append([demo_data_acs[epsd][transition]])
                goals.append([demo_data_obs[epsd][transition].get('desired_goal')])
                achieved_goals.append([demo_data_obs[epsd][transition].get('achieved_goal')])
                for idx, key in enumerate(info_keys):
                    info_values[idx][transition, i] = demo_data_info[epsd][transition][key]

            obs.append([demo_data_obs[epsd][self.T - 1].get('observation')])
            achieved_goals.append([demo_data_obs[epsd][self.T - 1].get('achieved_goal')])

            episode = dict(observations=obs,
                           u=acts,
                           g=goals,
                           ag=achieved_goals)
            for key, value in zip(info_keys, info_values):
                episode['info_{}'.format(key)] = value

            episode = convert_episode_to_batch_major(episode)
            global DEMO_BUFFER
            DEMO_BUFFER.ddpg_store_episode(episode) # create the observation dict and append them into the demonstration buffer
            logger.debug("Demo buffer size currently ", DEMO_BUFFER.get_current_size()) #print out the demonstration buffer size

            if update_stats:
                # add transitions to normalizer to normalize the demo data as well
                episode['o_2'] = episode['o'][:, 1:, :]
                episode['ag_2'] = episode['ag'][:, 1:, :]
                num_normalizing_transitions = transitions_in_episode_batch(episode)
                transitions = self.sample_transitions(episode, num_normalizing_transitions)

                o, g, ag = transitions['o'], transitions['g'], transitions['ag']
                transitions['o'], transitions['g'] = self._preprocess_og(o, ag, g)
                # No need to preprocess the o_2 and g_2 since this is only used for stats

                self.o_stats.update(transitions['o'])
                self.g_stats.update(transitions['g'])

                self.o_stats.recompute_stats()
                self.g_stats.recompute_stats()
            episode.clear()

        logger.info("Demo buffer size: ", DEMO_BUFFER.get_current_size()) # print out the demonstration buffer size

    def ddpg_store_episode(self, episode_batch, update_stats=True):
        """
        episode_batch: array of batch_size x (T or T+1) x dim_key
                       'o' is of size T+1, others are of size T
        """

        self.buffer.store_episode(episode_batch)

        if update_stats:
            # add transitions to normalizer
            episode_batch['o_2'] = episode_batch['o'][:, 1:, :]
            episode_batch['ag_2'] = episode_batch['ag'][:, 1:, :]
            num_normalizing_transitions = transitions_in_episode_batch(episode_batch)
            transitions = self.sample_transitions(episode_batch, num_normalizing_transitions)

            o, g, ag = transitions['o'], transitions['g'], transitions['ag']
            transitions['o'], transitions['g'] = self._preprocess_og(o, ag, g)
            # No need to preprocess the o_2 and g_2 since this is only used for stats

            self.o_stats.update(transitions['o'])
            self.g_stats.update(transitions['g'])

            self.o_stats.recompute_stats()
            self.g_stats.recompute_stats()

    def get_current_buffer_size(self):
        return self.buffer.get_current_size()

    def _sync_optimizers(self):
        self.critic_optimiser.sync()
        self.actor_optimiser.sync()

    def _grads(self):
        # Avoid feed_dict here for performance!
        critic_loss, actor_loss, critic_grad, actor_grad = self.sess.run([
            self.critic_loss_tf,  # MSE of target_tf - main.critic_tf
            self.main.critic_with_actor_tf,  # actor_loss
            self.critic_grads,
            self.actor_grads
        ])
        return critic_loss, actor_loss, critic_grad, actor_grad

    def _update(self, critic_grads, actor_grads):
        self.critic_optimiser.update(critic_grads, self.Q_lr)
        self.actor_optimiser.update(actor_grads, self.pi_lr)

    def sample_batch(self):
        if self.bc_loss:  # use demonstration buffer to sample as well if bc_loss flag is set TRUE
            print("Using demonstration buffer samples")
            transitions = self.buffer.sample(self.batch_size - self.demo_batch_size)
            global DEMO_BUFFER
            transitions_demo = DEMO_BUFFER.sample(self.demo_batch_size)  # sample from the demo buffer
            for k, values in transitions_demo.items():
                rolloutV = transitions[k].tolist()
                for v in values:
                    rolloutV.append(v.tolist())
                transitions[k] = np.array(rolloutV)
        else:
            transitions = self.buffer.sample(self.batch_size)  # otherwise only sample from primary buffer

        o, o_2, g = transitions['o'], transitions['o_2'], transitions['g']
        ag, ag_2 = transitions['ag'], transitions['ag_2']
        transitions['o'], transitions['g'] = self._preprocess_og(o, ag, g)
        transitions['o_2'], transitions['g_2'] = self._preprocess_og(o_2, ag_2, g)

        transitions_batch = [transitions[key] for key in self.stage_shapes.keys()]
        return transitions_batch

    def stage_batch(self, batch=None):
        if batch is None:
            batch = self.sample_batch()
        assert len(self.buffer_ph_tf) == len(batch)
        self.sess.run(self.stage_op, feed_dict=dict(zip(self.buffer_ph_tf, batch)))

    def ddpg_train(self, stage=True):
        if stage:
            self.stage_batch()

        self.critic_loss, self.actor_loss, Q_grad, pi_grad = self._grads()

        # Update gradients for actor and critic networks
        self._update(Q_grad, pi_grad)

        return self.critic_loss, np.mean(self.actor_loss)

    def _init_target_net(self):
        self.sess.run(self.init_target_net_op)

    def ddpg_update_target_net(self):
        self.sess.run(self.update_target_net_op)

    def clear_buffer(self):
        self.buffer.clear_buffer()

    def _vars(self, scope):
        res = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES, scope=self.scope + '/' + scope)
        assert len(res) > 0
        return res

    def _global_vars(self, scope):
        res = tf.get_collection(tf.GraphKeys.GLOBAL_VARIABLES, scope=self.scope + '/' + scope)
        return res

    def _create_network(self, reuse=False):
        logger.info("Creating a DDPG agent with action space %d x %s..." % (self.dimu, self.action_scale))
        self.sess = tf_util.get_session()

        # running averages
        with tf.variable_scope('o_stats') as variable_scope:
            if reuse:
                variable_scope.reuse_variables()
            self.o_stats = Normalizer(self.dimo, self.norm_eps, self.norm_clip, sess=self.sess)
        with tf.variable_scope('g_stats') as variable_scope:
            if reuse:
                variable_scope.reuse_variables()
            self.g_stats = Normalizer(self.dimg, self.norm_eps, self.norm_clip, sess=self.sess)

        # mini-batch sampling.
        batch = self.staging_tf.get()
        batch_tf = OrderedDict([(key, batch[i])
                                for i, key in enumerate(self.stage_shapes.keys())])
        batch_tf['r'] = tf.reshape(batch_tf['r'], [-1, 1])

        # choose only the demo buffer samples
        mask = np.concatenate((np.zeros(self.batch_size - self.demo_batch_size), np.ones(self.demo_batch_size)), axis=0)

        # networks
        with tf.variable_scope('main') as variable_scope:
            if reuse:
                variable_scope.reuse_variables()

            # Create actor critic network
            self.main = self.create_actor_critic(batch_tf, net_type='main', **self.__dict__)
            variable_scope.reuse_variables()

        with tf.variable_scope('target') as variable_scope:
            if reuse:
                variable_scope.reuse_variables()
            target_batch_tf = batch_tf.copy()
            target_batch_tf['o'] = batch_tf['o_2']
            target_batch_tf['g'] = batch_tf['g_2']
            self.target = self.create_actor_critic(
                target_batch_tf, net_type='target', **self.__dict__)
            variable_scope.reuse_variables()
        assert len(self._vars("main")) == len(self._vars("target"))

        # loss functions
        target_critic_actor_tf = self.target.critic_with_actor_tf
        clip_range = (-self.clip_return, 0. if self.clip_pos_returns else np.inf)

        target_tf = tf.clip_by_value(batch_tf['r'] + self.gamma * target_critic_actor_tf, *clip_range)

        # MSE of target_tf - critic_tf
        self.critic_loss_tf = tf.reduce_mean(tf.square(tf.stop_gradient(target_tf) - self.main.critic_tf))

        # # train with demonstrations and use bc_loss and q_filter both
        # if self.bc_loss == 1 and self.q_filter == 1:
        #     print("Training with demonstration")
        #     # where is the demonstrator action better than actor action according to the critic? choose samples only
        #     maskMain = tf.reshape(tf.boolean_mask(self.main.critic_tf > self.main.critic_actor_tf, mask), [-1])
        #     # define the cloning loss on the actor's actions only on the samples which adhere to the above masks
        #     self.cloning_loss_tf = tf.reduce_sum(tf.square(tf.boolean_mask(tf.boolean_mask((self.main.actor_tf), mask), maskMain, axis=0) - tf.boolean_mask(tf.boolean_mask((batch_tf['u']), mask), maskMain, axis=0)))
        #     # primary loss scaled by it's respective weight prm_loss_weight
        #     self.actor_loss_tf = -self.prm_loss_weight * tf.reduce_mean(self.main.critic_actor_tf)
        #     # L2 loss on action values scaled by the same weight prm_loss_weight
        #     self.actor_loss_tf += self.prm_loss_weight * self.action_l2 * tf.reduce_mean(tf.square(self.main.actor_tf / self.max_u))
        #     # adding the cloning loss to the actor loss as an auxiliary loss scaled by its weight aux_loss_weight
        #     self.actor_loss_tf += self.aux_loss_weight * self.cloning_loss_tf
        #
        # elif self.bc_loss == 1 and self.q_filter == 0: # train with demonstrations without q_filter
        #     self.cloning_loss_tf = tf.reduce_sum(tf.square(tf.boolean_mask((self.main.actor_tf), mask) - tf.boolean_mask((batch_tf['u']), mask)))
        #     self.actor_loss_tf = -self.prm_loss_weight * tf.reduce_mean(self.main.critic_actor_tf)
        #     self.actor_loss_tf += self.prm_loss_weight * self.action_l2 * tf.reduce_mean(tf.square(self.main.actor_tf / self.max_u))
        #     self.actor_loss_tf += self.aux_loss_weight * self.cloning_loss_tf
        #
        # else:  # If  not training with demonstrations

        print("Not training with demonstration")
        self.actor_loss_tf = -tf.reduce_mean(self.main.critic_with_actor_tf)
        self.actor_loss_tf += self.action_l2 * tf.reduce_mean(tf.square(self.main.actor_tf / self.action_scale))

        # Constructs symbolic derivatives of sum of critic_loss_tf vs _vars('main/Q')
        critic_grads_tf = tf.gradients(self.critic_loss_tf, self._vars('main/Q'))
        actor_grads_tf = tf.gradients(self.actor_loss_tf, self._vars('main/pi'))
        assert len(self._vars('main/Q')) == len(critic_grads_tf)
        assert len(self._vars('main/pi')) == len(actor_grads_tf)
        self.critic_grads_vars_tf = zip(critic_grads_tf, self._vars('main/Q'))
        self.actor_grads_vars_tf = zip(actor_grads_tf, self._vars('main/pi'))

        # Flattens variables and their gradients.
        self.critic_grads = flatten_grads(grads=critic_grads_tf, var_list=self._vars('main/Q'))
        self.actor_grads = flatten_grads(grads=actor_grads_tf, var_list=self._vars('main/pi'))

        # optimizers
        self.critic_optimiser = MpiAdam(self._vars('main/Q'), scale_grad_by_procs=False)
        self.actor_optimiser = MpiAdam(self._vars('main/pi'), scale_grad_by_procs=False)

        # polyak averaging used to update target network
        self.main_vars = self._vars('main/Q') + self._vars('main/pi')
        self.target_vars = self._vars('target/Q') + self._vars('target/pi')
        self.stats_vars = self._global_vars('o_stats') + self._global_vars('g_stats')

        # list( map( lambda( assign() ), zip()))
        self.init_target_net_op = list(
            map(    # Apply lambda to each item item in the zipped list
                lambda v: v[0].assign(v[1]),
                zip(self.target_vars, self.main_vars))
            )

        # Polyak-Ruppert averaging where most recent iterations are weighted more than past iterations.
        self.update_target_net_op = list(
            map(    # Apply lambda to each item item in the zipped list
                lambda v: v[0].assign(self.polyak * v[0] + (1. - self.polyak) * v[1]),  # polyak averaging
                zip(self.target_vars, self.main_vars))  # [(target_vars, main_vars), (), ...]
            )

        # initialize all variables
        tf.variables_initializer(self._global_vars('')).run()
        self._sync_optimizers()
        self._init_target_net()

    def logs(self, prefix=''):
        logs = []
        # logs += [('actor_critic/critic_loss', critic_loss_avg)]
        # logs += [('actor_critic/actor_loss', actor_loss_avg)]

        logs += [('stats_o/mean', np.mean(self.sess.run([self.o_stats.mean])))]
        logs += [('stats_o/std', np.mean(self.sess.run([self.o_stats.std])))]
        logs += [('stats_g/mean', np.mean(self.sess.run([self.g_stats.mean])))]
        logs += [('stats_g/std', np.mean(self.sess.run([self.g_stats.std])))]

        if prefix != '' and not prefix.endswith('/'):
            return [(prefix + '/' + key, val) for key, val in logs]
        else:
            return logs

    def __getstate__(self):
        """Our policies can be loaded from pkl, but after unpickling you cannot continue training.
        """
        excluded_subnames = ['_tf', '_op', '_vars', '_adam', 'buffer', 'sess', '_stats',
                             'main', 'target', 'lock', 'env', 'sample_transitions',
                             'stage_shapes', 'create_actor_critic']

        state = {k: v for k, v in self.__dict__.items() if all([not subname in k for subname in excluded_subnames])}
        state['buffer_size'] = self.buffer_size
        state['tf'] = self.sess.run([x for x in self._global_vars('') if 'buffer' not in x.name])
        return state

    def __setstate__(self, state):
        if 'sample_transitions' not in state:
            # We don't need this for playing the policy.
            state['sample_transitions'] = None

        self.__init__(**state)
        # set up stats (they are overwritten in __init__)
        for k, v in state.items():
            if k[-6:] == '_stats':
                self.__dict__[k] = v
        # load TF variables
        vars = [x for x in self._global_vars('') if 'buffer' not in x.name]
        assert(len(vars) == len(state["tf"]))
        node = [tf.assign(var, val) for var, val in zip(vars, state["tf"])]
        self.sess.run(node)

    def save(self, save_path):
        tf_util.save_variables(save_path)
