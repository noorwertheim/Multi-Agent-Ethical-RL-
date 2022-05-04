# Multi-Agent-Ethical-Reinforcement-Learning
## Thesis project in which agents are trained to behave ethically using Deep Reinforcement Learning



**Environment**

The environment used is the Lumberjack-v0 environment from https://github.com/koulanurag/ma-gym. In this environment two agents/lumberjacks are rewarded when they cut a tree. When the tree strenght of a tree is equal to 2, it takes two agents to cut the tree togeter. I slightly modified this environment, so that all tree strengths are equal to 1, so cooperation is not an element of the environment anymore. Also, instead of two equal agents, I made one 'weak' agent and one 'strong' agent. The weak agent can only cut trees in a certain percentage of the time. This percentage is yet to be determined. 

**Deontic vs. Consequentialistic value embedding**
There are two different versions of the environment. lumberjacks_deontic.py and lumberjacks_consequentialistic.py. The difference is in the way the values are embedded. In the deontic version, behavioral rules are hardcoded. If a certain agent has more trees than the other one, he is not able to cut any more trees. 
In the consequentialist version, the reward function determines the behavior of the agent rather than hardcoded rules. If the other agent has less trees, the reward for cutting a tree will be lower. 

**Value Decomposition Network**
The agents are trained using a Value Decomposition Network. This algorithm is found in vdn.py. The one used here is from https://github.com/koulanurag/minimal-marl. 
