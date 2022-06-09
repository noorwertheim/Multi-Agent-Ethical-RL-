import argparse
import collections

import gym
import numpy as np
from sklearn.tree import plot_tree
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import matplotlib.pyplot as plt


USE_WANDB = True # if enabled, logs data on wandb server

def plot_trees(treescut_weak, treescut_strong):
    x = [*range(0, len(treescut_weak) * 10, 10)]
    print(x)
    plt.plot(x, treescut_weak, label='total trees cut per episode agent 1')
    plt.plot(x, treescut_strong, label='total trees cut per episode agent 2')
    plt.xlabel('Episodes')
    plt.ylabel('Trees cut per episode')
    plt.legend()
    plt.show()

class ReplayBuffer:
    def __init__(self, buffer_limit):
        self.buffer = collections.deque(maxlen=buffer_limit)

    def put(self, transition):
        self.buffer.append(transition)

    def sample_chunk(self, batch_size, chunk_size):
        start_idx = np.random.randint(0, len(self.buffer) - chunk_size, batch_size)
        s_lst, a_lst, r_lst, s_prime_lst, done_lst = [], [], [], [], []

        for idx in start_idx:
            for chunk_step in range(idx, idx + chunk_size):
                s, a, r, s_prime, done = self.buffer[chunk_step]
                s_lst.append(s)
                a_lst.append(a)
                r_lst.append(r)
                s_prime_lst.append(s_prime)
                done_lst.append(done)

        n_agents, obs_size = len(s_lst[0]), len(s_lst[0][0])
        return torch.tensor(s_lst, dtype=torch.float).view(batch_size, chunk_size, n_agents, obs_size), \
               torch.tensor(a_lst, dtype=torch.float).view(batch_size, chunk_size, n_agents), \
               torch.tensor(r_lst, dtype=torch.float).view(batch_size, chunk_size, n_agents), \
               torch.tensor(s_prime_lst, dtype=torch.float).view(batch_size, chunk_size, n_agents, obs_size), \
               torch.tensor(done_lst, dtype=torch.float).view(batch_size, chunk_size, 1)

    def size(self):
        return len(self.buffer)


class QNet(nn.Module):
    def __init__(self, observation_space, action_space, recurrent=False):
        super(QNet, self).__init__()
        self.num_agents = len(observation_space)
        self.recurrent = recurrent
        self.hx_size = 32
        for agent_i in range(self.num_agents):
            n_obs = observation_space[agent_i].shape[0]
            setattr(self, 'agent_feature_{}'.format(agent_i), nn.Sequential(nn.Linear(n_obs, 64),
                                                                            nn.ReLU(),
                                                                            nn.Linear(64, self.hx_size),
                                                                            nn.ReLU()))
            if recurrent:
                setattr(self, 'agent_gru_{}'.format(agent_i), nn.GRUCell(self.hx_size, self.hx_size))
            setattr(self, 'agent_q_{}'.format(agent_i), nn.Linear(self.hx_size, action_space[agent_i].n))

    def forward(self, obs, hidden):
        q_values = [torch.empty(obs.shape[0], )] * self.num_agents
        next_hidden = [torch.empty(obs.shape[0], 1, self.hx_size)] * self.num_agents
        for agent_i in range(self.num_agents):
            x = getattr(self, 'agent_feature_{}'.format(agent_i))(obs[:, agent_i, :])
            if self.recurrent:
                x = getattr(self, 'agent_gru_{}'.format(agent_i))(x, hidden[:, agent_i, :])
                next_hidden[agent_i] = x.unsqueeze(1)
            q_values[agent_i] = getattr(self, 'agent_q_{}'.format(agent_i))(x).unsqueeze(1)

        return torch.cat(q_values, dim=1), torch.cat(next_hidden, dim=1)

    def sample_action(self, obs, hidden, epsilon):
        out, hidden = self.forward(obs, hidden)
        mask = (torch.rand((out.shape[0],)) <= epsilon)
        action = torch.empty((out.shape[0], out.shape[1],))
        action[mask] = torch.randint(0, out.shape[2], action[mask].shape).float()
        action[~mask] = out[~mask].argmax(dim=2).float()
        return action, hidden

    def init_hidden(self, batch_size=1):
        return torch.zeros((batch_size, self.num_agents, self.hx_size))


def train(q, q_target, memory, optimizer, gamma, batch_size, update_iter=10, chunk_size=10, grad_clip_norm=5):
    _chunk_size = chunk_size if q.recurrent else 1
    for _ in range(update_iter):
        s, a, r, s_prime, done = memory.sample_chunk(batch_size, _chunk_size)

        hidden = q.init_hidden(batch_size)
        target_hidden = q_target.init_hidden(batch_size)
        loss = 0
        for step_i in range(_chunk_size):
            q_out, hidden = q(s[:, step_i, :, :], hidden)
            q_a = q_out.gather(2, a[:, step_i, :].unsqueeze(-1).long()).squeeze(-1)
            sum_q = q_a.sum(dim=1, keepdims=True)

            max_q_prime, target_hidden = q_target(s_prime[:, step_i, :, :], target_hidden.detach())
            max_q_prime = max_q_prime.max(dim=2)[0].squeeze(-1)
            target_q = r[:, step_i, :].sum(dim=1, keepdims=True)
            target_q += gamma * max_q_prime.sum(dim=1, keepdims=True) * (1 - done[:, step_i])

            loss += F.smooth_l1_loss(sum_q, target_q.detach())

            done_mask = done[:, step_i].squeeze(-1).bool()
            hidden[done_mask] = q.init_hidden(len(hidden[done_mask]))
            target_hidden[done_mask] = q_target.init_hidden(len(target_hidden[done_mask]))

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(q.parameters(), grad_clip_norm, norm_type=2)
        optimizer.step()


def test(env, num_episodes, q):
    score = 0
    ethical_score = 0
    individual_score = 0
    ethical_reward_tot = np.zeros(2)
    individual_reward_tot = np.zeros(2)
    for episode_i in range(num_episodes):
        state = env.reset()
        done = [False for _ in range(env.n_agents)]
        with torch.no_grad():
            hidden = q.init_hidden()
            while not all(done):
                action, hidden = q.sample_action(torch.Tensor(state).unsqueeze(0), hidden, epsilon=0)
                next_state, reward, done, info, ethical_reward, individual_reward = env.step(action[0].data.cpu().numpy().tolist())
                score += sum(reward)
                ethical_score += sum(ethical_reward)
                individual_score += sum(individual_reward)
                ethical_reward_tot += ethical_reward
                individual_reward_tot += individual_reward

                state = next_state


    return score / num_episodes, ethical_score / num_episodes, individual_score / num_episodes, ethical_reward_tot / num_episodes, individual_reward_tot / num_episodes


def main(env_name, lr, gamma, batch_size, buffer_limit, log_interval, max_episodes, max_epsilon, min_epsilon,
         test_episodes, warm_up_steps, update_iter, chunk_size, update_target_interval, recurrent):

    # create env.
    env = gym.make(env_name)
    test_env = gym.make(env_name)
    memory = ReplayBuffer(buffer_limit)
    trees_cut_weak = []
    trees_cut_strong = []
    trees_cut_weak_test = []
    trees_cut_strong_test = []

    # create networks
    q = QNet(env.observation_space, env.action_space, recurrent)
    q_target = QNet(env.observation_space, env.action_space, recurrent)
    q_target.load_state_dict(q.state_dict())
    optimizer = optim.Adam(q.parameters(), lr=lr)

    score = 0
    ethical_score = 0
    individual_score = 0
    
    for episode_i in range(max_episodes):
        epsilon = max(min_epsilon, max_epsilon - (max_epsilon - min_epsilon) * (episode_i / (0.6 * max_episodes)))
        state = env.reset()
        done = [False for _ in range(env.n_agents)]
        with torch.no_grad():
            hidden = q.init_hidden()
            while not all(done):
                action, hidden = q.sample_action(torch.Tensor(state).unsqueeze(0), hidden, epsilon)
                action = action[0].data.cpu().numpy().tolist()
                next_state, reward, done, info, ethical_reward, individual_reward = env.step(action)
                memory.put((state, action, (np.array(reward)).tolist(), next_state, [int(all(done))]))
                score += sum(reward)
                ethical_score += sum(ethical_reward)
                individual_score += sum(individual_reward)
                
                state = next_state

        if memory.size() > warm_up_steps:
            train(q, q_target, memory, optimizer, gamma, batch_size, update_iter, chunk_size)

        if episode_i % update_target_interval:
            q_target.load_state_dict(q.state_dict())

        if (episode_i + 1) % log_interval == 0:
            test_score = test(test_env, test_episodes, q)[0]
            train_score = score / log_interval
            test_ethical = test(test_env, test_episodes, q)[1]
            train_ethical = ethical_score / log_interval
            test_individual = test(test_env, test_episodes, q)[2]
            train_individual = individual_score / log_interval
            ethical_reward_tot = test(test_env, test_episodes, q)[3]
            individual_reward_tot = test(test_env, test_episodes, q)[4]
            print("#{:<10}/{} episodes , avg train score : {:.1f}, test score: {:.1f} n_buffer : {}, eps : {:.1f}"
                  .format(episode_i, max_episodes, train_score, test_score, memory.size(), epsilon))
            print('ethical_test_score', test_ethical, 'individual_test_score', test_individual)
            trees_cut_weak.append(env._total_trees_cut[1])
            trees_cut_strong.append(env._total_trees_cut[0])
            trees_cut_weak_test.append(test_env._total_trees_cut[1])
            trees_cut_strong_test.append(test_env._total_trees_cut[0])
            
            if USE_WANDB:
                wandb.log({'episode': episode_i, 'test-score': test_score, 'ethical-test-score': test_ethical, 'individual-test-score': test_individual, 'buffer-size': memory.size(),
                           'epsilon': epsilon, 'train-score': train_score, 'ethical-train-score': train_ethical, 'individual-train-score': train_individual, 'ethical-test-agent0': ethical_reward_tot[0], 'ethical-test-agent1': ethical_reward_tot[1], 'individual-test-agent0': individual_reward_tot[0], 'individual-test-agent1': individual_reward_tot[1]})
            score = 0
            ethical_score = 0
            individual_score = 0

    print('trees_cut_weak = ', trees_cut_weak)
    print('trees_cut_strong = ', trees_cut_strong)
    print('trees_cut_weak_test = ', trees_cut_weak_test)
    print('trees_cut_strong_test = ', trees_cut_strong_test)
    env.close()
    test_env.close()

if __name__ == '__main__':
    # Lets gather arguments
    parser = argparse.ArgumentParser(description='Value Decomposition Network (VDN)')
    parser.add_argument('--env-name', required=False, default='ma_gym:Lumberjacks-v0')
    parser.add_argument('--seed', type=int, default=1, required=False)
    parser.add_argument('--no-recurrent', action='store_true')
    parser.add_argument('--max-episodes', type=int, default=10000, required=False)

    # Process arguments
    args = parser.parse_args()

    kwargs = {'env_name': args.env_name,
              'lr': 0.001,
              'batch_size': 32,
              'gamma': 0.99,
              'buffer_limit': 50000,
              'update_target_interval': 20,
              'log_interval': 100,
              'max_episodes': args.max_episodes,
              'max_epsilon': 0.9,
              'min_epsilon': 0.1,
              'test_episodes': 5,
              'warm_up_steps': 2000,
              'update_iter': 10,
              'chunk_size': 10,  # if not recurrent, internally, we use chunk_size of 1 and no gru cell is used.
              'recurrent': not args.no_recurrent}

    if USE_WANDB:
        import wandb

        wandb.init(project='minimal-marl', config={'algo': 'vdn', **kwargs})

    main(**kwargs)

