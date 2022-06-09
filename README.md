# Multi-Agent-Ethical-Reinforcement-Learning
## Thesis project in which agents are trained to behave ethically using Deep Reinforcement Learning



**Environment**

The environment used is the Lumberjack-v0 environment from https://github.com/koulanurag/ma-gym. In this environment two agents/lumberjacks are rewarded when they cut a tree. When the tree strenght of a tree is equal to 2, it takes two agents to cut the tree togeter. I slightly modified this environment, so that all tree strengths are equal to 1, so cooperation is not an element of the environment anymore. Also, instead of two equal agents, I made one 'weak' agent and one 'strong' agent. The weak agent can only cut trees in a certain percentage of the time. This percentage is yet to be determined. 

**Ethical Value Embedding**

An ethical objective was added to the lumberjacks environment, according to the method of Rodriguez-Soto et al. (2022). Using this method, the agents were trained to behave ethically, and each cut an equal amount of trees.

**Value Decomposition Network**

The agents are trained using a Value Decomposition Network. This algorithm is found in vdn.py. The one used here is from https://github.com/koulanurag/minimal-marl. 


**File Descriptions**

<u>lumberjacks.py</u> Used for running the vdn algorithm. Paste in here which version of the Lumberjacks environment you want to use. 
<u>lumberjacks_ethial.py</u> Lumberjacks environment with ethical embedding. This version trains two agents using the same reward function. 
<u>lumberjacks_ethial2.py</u> Lumberjacks environment with ethical embedding. This version trains two agents using different reward functions. 
<u>lumberjacks_strong_strong.py</u> Lumberjacks environment with no ethical embedding and two equally strong agents. 
<u>lumberjacks_weak_strong.py</u> Lumberjacks environment with no ethical embedding and a weak and a strong angent. 
<u>vdn_ethical</u> Value decomposition network adjusted to the ethical lumberjacks environments. This implementation is for training the agents using the same reward function.  
<u>vdn_ethical</u> Value decomposition network adjusted to the ethical lumberjacks environments. This implementation is for training the agents using different reward functions. 


**References**

Koul, A. (2019). ma-gym: Collection of multi-agent environments based on openai
  gym. https://github.com/koulanurag/ma-gym.

Koul, A. (2021). minimal-marl: Minimal implementation of multi-agent reinforce-
  ment learning algorithms. https://github.com/koulanurag/minimal-marl.
  git.

Rodriguez-Soto, M., Serramia, M., Lopez-Sanchez, M., and Rodriguez-Aguilar,
  J. A. (2022). Instilling moral value alignment by means of multi-objective rein-
  forcement learning. Ethics and Information Technology, 24(1):1–17
  
