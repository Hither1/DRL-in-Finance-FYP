"""
Created on 4 May, 2021

@author: Huangyuan

This script is about
adding penalty that is constant for each step

The backward update algo now has F and H factors

We see how the backward update performs in simple/windy gridworlds

"""

from envs.DoughVeg_gridworld import GridworldEnv
#from envs.DoughVeg_windy import GridworldEnv
import numpy as np
import pandas as pd
import sys
from collections import defaultdict
import matplotlib.pyplot as plt
from scipy.special import softmax
import time

current_env_windy = False  # Change between normal/windy gridworlds

discount_factor = 1
discounting = 'hyper'  # 'hyper', 'exp'
init_policy = 'random'  # 'random' 'stable'

alpha = .37  # The noise parameter that modulates between random choice (=0) and perfect maximization (=\infty)
epsilon = .1
num_episodes = 80000  # 0000
penalty = 0.8

env = GridworldEnv()

if current_env_windy:
    is_wall = lambda s: s in [6, 13, 20, 27, 35, 36, 37, 38, 39]  # windy gridworld
else:
    is_wall = lambda s: s in [6, 10, 14, 18]


def auto_discounting(discount_factor=discount_factor):
    def hyper(i, discount_factor=discount_factor):
        print(i)
        return 1 / (1 + discount_factor * i)

    def exp(i, discount_factor=discount_factor):
        return discount_factor ** i

    if discounting == 'hyper':
        return hyper
    else:
        return exp


def make_policy(Q, epsilon, nA):
    """
    Creates an probabilistic policy based on a given expected Utility function and alpha.

    Args:
        expUtility: A dictionary that maps from (state, delay) -> action-values.
            Each value is a numpy array of length nA (see below)
        alpha: moderating parameter

    Returns:
        A function that takes the observation(state, delay) as an argument and returns
        an action according to the probabilities for each action.

    """

    def policy_fn(observation):
        A = np.ones(nA, dtype=float) * epsilon / nA
        best_action = np.argmax(Q[observation])
        A[best_action] += (1.0 - epsilon)

        return A

    return policy_fn


# Hyperbolic Discounted Q-learning (off-policy TD control)
def td_control(env, num_episodes, step_size):
    global q_correction_21, q_u, q_r, q_b, q_l

    # The type of discounting
    discount = auto_discounting()

    # Global variables
    global critical_episode_9, critical_episode_21

    # We store the values in the order Q[state][action]
    Q = defaultdict(lambda: np.zeros(env.action_space.n))
    if current_env_windy:  # windy gridworld -
        for a in range(env.action_space.n):
            Q[10][a] = 3
            Q[28][a] = 10
            Q[4][a] = 6
    else:
        for a in range(env.action_space.n):
            Q[2][a] = 19
            Q[8][a] = 10
    # f[n][state][action], n is the time at which we take expectation
    f = defaultdict(lambda: defaultdict(lambda: np.zeros(env.action_space.n)))
    # h[m][n][state][action], m is the time when the reward happened, n is the time at which we take expectation
    h = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: np.zeros(env.action_space.n))))

    # Take the Utility function from reward function of the environment
    # Utility = env.copy_reward_fn
    agent = make_policy(Q, epsilon, env.action_space.n)

    for i_episode in range(1, num_episodes + 1):
        if current_env_windy:
            print("Q[4]", Q[4])
            print("Q[10]", Q[10])
            print("Q[28]", Q[28])
        else:
            print("Q[2]", Q[2])
            print("Q[8]", Q[8])

        # Print out which episode we're on, useful for debugging.
        if i_episode % 1000 == 0:
            print("\rEpisode {}/{}.".format(i_episode, num_episodes), end="")
            sys.stdout.flush()

        # Generate an episode.
        # An episode is an array of (state, action, reward) tuples
        episode = []
        state = env.reset()

        if is_wall(state) or state == 2 or state == 8:
            # print('init on wall, skip')
            continue

        print_trajectory = False

        # Sample a new trajectory
        for t in range(100):
            probs = agent(state)  # Select an action according to policy
            if current_env_windy and state == 31:
                action = 0
            else:
                action = np.random.choice(np.arange(len(probs)), p=probs)
                # action = np.argmax(Q[state])

            next_state, reward, done, _ = env.step(action)

            # for each m, update all n that n <= t
            for n in range(0, t):
                h[t][n][state][action] = -1 * penalty

            if next_state != state:
                episode.append((state, action, reward))
            # if final state
            if done:
                print("current", state)
                print("next", next_state)
                print("Ending state", state)
                if current_env_windy:
                    if next_state == 4:
                        episode.append((next_state, np.argmax(Q[state]), 6))
                    elif next_state == 10:
                        episode.append((next_state, np.argmax(Q[state]), 3))
                    elif next_state == 28:
                        episode.append((next_state, np.argmax(Q[state]), 10))
                else:
                    if next_state == 2:
                        episode.append((next_state, np.argmax(Q[state]), 19))
                    elif next_state == 8:
                        episode.append((next_state, np.argmax(Q[state]), 10))
                break
            state = next_state  # update to the next state
        # Offline update, backward
        # 1. Initialize the boundary values for f
        if current_env_windy:
            for a in range(env.action_space.n):
                if next_state == 4:
                    f[len(episode) - 1][4][a] = 6
                    f[len(episode) - 1][10][a] = 0
                    f[len(episode) - 1][28][a] = 0
                elif next_state == 10:
                    f[len(episode) - 1][4][a] = 0
                    f[len(episode) - 1][10][a] = 3
                    f[len(episode) - 1][28][a] = 0
                elif next_state == 28:
                    f[len(episode) - 1][4][a] = 0
                    f[len(episode) - 1][10][a] = 0
                    f[len(episode) - 1][28][a] = 10
        else:
            for a in range(env.action_space.n):
                if next_state == 2:
                    f[len(episode) - 1][2][a] = 19
                    f[len(episode) - 1][8][a] = 0
                elif next_state == 8:
                    f[len(episode) - 1][2][a] = 0
                    f[len(episode) - 1][8][a] = 10
        # 2. others
        print("Start to view the episode")
        for t in range(len(episode) - 2, -1, -1):
            s, a, r = episode[t]
            next_state, next_action, next_r = episode[t + 1]
            print(episode)
            # Update (g, h,) f
            # f should be the expected value of all its next states
            nA = env.action_space.n
            # s_prime = []
            # Calculate for next state
            # Update f factor
            f[t][s][a] = max(f[t + 1][next_state]) / discount(len(episode) - 1 - (t + 1)) * discount(
                len(episode) - 1 - t)
            # Update h factor(s)
            for m in range(t + 1, len(episode)):
                h[m][t][s][a] = max(h[m][t + 1][next_state]) / discount(m - (t + 1)) * discount(m - t)

            print("len of episode", len(episode))
            print(f[len(episode) - 1][2], f[len(episode) - 1][8])
            print("f[t][s][a]", f[t][s][a])
            print("Q next state", max(Q[next_state]), "where next state is", next_state)

            # Update Q
            # Q[s][a] = max(Q[next_state]) - (
            #         max(f[t+1][next_state]) - f[t][s][a])
            Q[s][a] = Q[s][a] + alpha * (max(Q[next_state]) - (
                    max(f[t + 1][next_state]) - f[t][s][a]) - Q[s][a]) \
                      + (-1 * penalty) - (sum([max(h[m][t + 1][next_state]) for m in range(t + 1, len(episode))]) - sum(
                [h[m][t][s][a] for m in range(t + 1, len(episode))]))
            print("Q[s][a], s, a", Q[s][a], s, a)

            '''
            if state == 25 and t == 0 and action == 1:
                print_trajectory = True

                print('----')
                print('s:', state)
                print('d:', t)
                print('a:', action)

                #print('probs:', probs)

                print('next_state:', next_state)
                print('reward:', reward)
                print('done:', done)
                #print('u:', u)

                print('t+1', t+1)
                for a_ in range(4):
                    print('a_:', a_)




            if state == 9 and action == 0:  # check for possible JUMP at 9 due to noisy policy

                if critical_episode_9 == 0:
                    critical_episode_9 = i_episode - 1

                # count_9 += 1

                #curr_policy = np.argmax(agent(state))
                curr_Q = Q[state][0]  # delay = 0
                #print('curr_policy_9:', curr_policy)
                #print('curr_Q[9]:', curr_Q)

                #print('-----')

            # if state == 21 and action == 1: # check for when the change to SPE is reflected at 21
            if state == 21 and Q[21][0][1] > Q[21][0][0]:

                if critical_episode_21 == 0:  # update the episode in which we reach state 21
                    critical_episode_21 = i_episode - 1

                # count_21 += 1

                #curr_policy = np.argmax(agent(state))
                curr_Q = Q[state][0]
                #print('curr_policy:', curr_policy)
                #print('curr_Q[21]:', curr_Q)

                # print('trajectory aft 21:', episode[first_occurence_idx:])


        if print_trajectory == True:
            print('episode:', episode)
            print('Q[s = 9][d = 0][a = 0]:', Q[9][0][0])

            #if f[9][0][0] > 10:
                #break
        '''
        if current_env_windy:
            # Track Q[24] for all actions and plot
            q_u.append([Q[24][0], Q[25][0], Q[31][0], Q[32][0]])
            q_r.append([Q[24][1], Q[25][1], Q[31][1], Q[32][1]])
            q_b.append([Q[24][2], Q[25][2], Q[31][2], Q[32][2]])
            q_l.append([Q[24][3], Q[25][3], Q[31][3], Q[32][3]])
        else:
            # Track Q[21] for all actions and plot
            q_u.append([Q[21][0], Q[9][0]])
            q_r.append([Q[21][1], Q[9][1]])
            q_b.append([Q[21][2], Q[9][2]])
            q_l.append([Q[21][3], Q[9][3]])

    return Q


# def calculate_expectation(f, t, s):


# Critical to check how sensitive is relevant states (i.e. 13, 17, 21) to sudden deviation at 9
critical_states_update_order = []
critical_index_9 = 0
critical_episode_9 = 0
critical_index_21 = 0
critical_episode_21 = 0

q_correction_21 = []
q_u = []
q_r = []
q_b = []
q_l = []
np.random.seed(0)

start = time.time()
Q = td_control(env, num_episodes, step_size=0.5)
end = time.time()

# print("[9].keys()")
# print(Q[9].keys())

# ------------------------------------------------------------------------------------------------

'''Checking criticals'''
print('EPSILON:', epsilon)
print('POLICY INIT:', init_policy)
print('DISCOUNTING:', discounting)
print('-----')
print('(9, UP) first appears at ep:', critical_episode_9)
print('visitation to 21 aft:', critical_states_update_order[critical_index_9:].count(21))
# print('(21, RIGHT) first appears at ep:', critical_episode_21)
print('Q(21, RIGHT) > Q(21, UP) first appears at ep:', critical_episode_21)
print('Time used: ', end - start)

if current_env_windy:
    x = [i for i in range(1, 1 + len(q_u))]
    # first pic
    fig, axs = plt.subplots(2, 2)
    axs[0, 0].plot(x, np.array(np.array(q_u)[:, 0]) - np.array(np.array(q_r)[:, 0]))
    axs[0, 0].set_title('Q(24, u) - Q(24, r) (Soph.)')
    axs[0, 1].plot(x, np.array(np.array(q_u)[:, 1]) - np.array(np.array(q_b)[:, 1]))
    axs[0, 1].set_title('Q(25, u) - Q(25, b) (Soph.)')
    axs[1, 0].plot(x, np.array(np.array(q_l)[:, 2]) - np.array(np.array(q_u)[:, 2]))
    axs[1, 0].set_title('Q(31, l) - Q(31, u) (Soph.)')
    axs[1, 1].plot(x, np.array(np.array(q_u)[:, 3]) - np.array(np.array(q_l)[:, 3]))
    axs[1, 1].set_title('Q(32, u) - Q(32, l) (Soph.)')

    fig.show()

    # second pic
    fig, axs = plt.subplots(2, 2)
    axs[0, 0].plot(x, np.array(q_u)[:, 0], label='u')
    axs[0, 0].plot(x, np.array(q_r)[:, 0], label='r')
    axs[0, 0].plot(x, np.array(q_b)[:, 0], label='b')
    axs[0, 0].plot(x, np.array(q_l)[:, 0], label='l')
    axs[0, 0].set_title('State 24 (Soph.)')
    axs[0, 0].legend()
    axs[0, 1].plot(x, np.array(q_u)[:, 1], label='u')
    axs[0, 1].plot(x, np.array(q_r)[:, 1], label='r')
    axs[0, 1].plot(x, np.array(q_b)[:, 1], label='b')
    axs[0, 1].plot(x, np.array(q_l)[:, 1], label='l')
    axs[0, 1].set_title('State 25 (Soph.)')
    axs[0, 1].legend()
    axs[1, 0].plot(x, np.array(q_u)[:, 2], label='u')
    axs[1, 0].plot(x, np.array(q_r)[:, 2], label='r')
    axs[1, 0].plot(x, np.array(q_b)[:, 2], label='b')
    axs[1, 0].plot(x, np.array(q_l)[:, 2], label='l')
    axs[1, 0].set_title('State 31 (Soph.)')
    axs[1, 0].legend()
    axs[1, 1].plot(x, np.array(q_u)[:, 3], label='u')
    axs[1, 1].plot(x, np.array(q_r)[:, 3], label='r')
    axs[1, 1].plot(x, np.array(q_b)[:, 3], label='b')
    axs[1, 1].plot(x, np.array(q_l)[:, 3], label='l')
    axs[1, 1].set_title('State 32 (Soph.)')
    axs[1, 1].legend()
    fig.show()

else:
    x = [i for i in range(1, 1 + len(q_u))]
    # first pic
    fig, axs = plt.subplots(1, 2)
    print("Final Q_u")
    # print(q_u)
    axs[0].plot(x, np.array(q_u)[:, 0] - np.array(q_r)[:, 0])
    axs[0].set_title('Difference Q(21, u) - Q(21, r) (Soph.)')
    axs[1].plot(x, np.array(q_l)[:, 1] - np.array(q_u)[:, 1])
    axs[1].set_title('Difference Q(9, l) - Q(9, u) (Soph.)')
    fig.suptitle('alpha ' + str(alpha) + ' epsilon ' + str(epsilon))
    fig.show()

    # second pic
    fig, axs = plt.subplots(1, 2)
    axs[0].plot(x, np.array(q_u)[:, 0], label='u')
    axs[0].plot(x, np.array(q_r)[:, 0], label='r')
    axs[0].plot(x, np.array(q_b)[:, 0], label='b')
    axs[0].plot(x, np.array(q_l)[:, 0], label='l')
    axs[0].set_title('Q(s=21) Soph.: Gridworld')
    axs[0].legend()
    axs[1].plot(x, np.array(q_u)[:, 1], label='u')
    axs[1].plot(x, np.array(q_r)[:, 1], label='r')
    axs[1].plot(x, np.array(q_b)[:, 1], label='b')
    axs[1].plot(x, np.array(q_l)[:, 1], label='l')
    axs[1].set_title('Q(s=9) Soph.: Gridworld')
    plt.legend()
    fig.suptitle('alpha ' + str(alpha) + ' epsilon ' + str(epsilon))
    fig.show()
