import tensorflow as tf
from baselines.her.util import store_args, create_nerual_net


class ActorCritic:
    @store_args
    def __init__(self, inputs_tf, dimo, dimg, dimu, max_u, o_stats, g_stats, hidden, layers,
                 **kwargs):
        """The actor-critic network and related training code.
        Args:
            inputs_tf (dict of tensors): all necessary inputs for the network: the
                observation (o), the goal (g), and the action (u)
            dimo (int): the dimension of the observations
            dimg (int): the dimension of the goals
            dimu (int): the dimension of the actions
            max_u (float): the maximum magnitude of actions; action outputs will be scaled
                accordingly
            o_stats (baselines.her.Normalizer): normalizer for observations
            g_stats (baselines.her.Normalizer): normalizer for goals
            hidden (int): number of hidden units that should be used in hidden layers
            layers (int): number of hidden layers
        """

        # Calls util.py stpre_args(method)
        self.o_tf = inputs_tf['o']
        self.g_tf = inputs_tf['g']
        self.u_tf = inputs_tf['u']
        print("INIT Actor-Critic with", hidden, "hidden units and ", layers, "hidden layers")
        # print("inputs_tf['u']", self.u_tf)
        # print("inputs_tf['o']", self.o_tf)
        # print("inputs_tf['g']", self.g_tf)

        # Prepare inputs for actor and critic.
        o = self.o_stats.normalize(self.o_tf)
        g = self.g_stats.normalize(self.g_tf)

        # Actor receives observation and goal to improve policy
        input_actor = tf.concat(axis=1, values=[o, g])  # for actor

        # Creates actor Actor network
        with tf.variable_scope('pi'):
            self.actor_tf = self.max_u * tf.tanh(create_nerual_net(
                input_actor, [self.hidden] * self.layers + [self.dimu]))

        # Creates actor Critic network
        with tf.variable_scope('Q'):
            # Critic receives obs, goals from env and output of actor as inputs
            input_critic = tf.concat(axis=1, values=[o, g, self.actor_tf / self.max_u])
            # For policy training
            self.critic_with_actor_tf = create_nerual_net(input_critic, [self.hidden] * self.layers + [1])

            # for Critic - Value Function training
            input_critic = tf.concat(axis=1, values=[o, g, self.u_tf / self.max_u])
            self._input_critic = input_critic  # exposed for tests
            self.critic_tf = create_nerual_net(input_critic, [self.hidden] * self.layers + [1], reuse=True)
