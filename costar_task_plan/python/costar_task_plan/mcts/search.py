
# By Chris Paxton
# (c) 2017 The Johns Hopkins University
# See License for more details

import timeit

from abstract import AbstractSearch
from node import Node

'''
Search through the tree exhaustively.
'''


class DepthFirstSearch(AbstractSearch):

    def __init__(self, policies):
        self.policies = policies

    def __call__(self, root, max_expansions=10, *args, **kwargs):
        start_time = timeit.default_timer()
        self.policies.initialize(root)
        nodes_to_visit = [root]

        best_reward = -float('inf')
        best_node = None

        while len(nodes_to_visit) > 0:
        # Get the next node to visit.
            node = nodes_to_visit.pop()

            if node.terminal:
                if node.accumulatedReward() > best_reward:
                    best_reward = node.accumulatedReward()
                    best_node = node
            else:
                expanded = 0
                # add any possible children from the root
                for child in node.children:
                    expanded += 1
                    self.policies.instantiate(node, child)
                    nodes_to_visit.append(child)

                    if expanded > max_expansions:
                        break

        path = []
        if best_node is not None:
            path.append(best_node)
            while best_node.parent is not None:
                best_node = best_node.parent

        path.reverse()

        elapsed = timeit.default_timer() - start_time
        return elapsed, path


class MonteCarloTreeSearch(AbstractSearch):

    '''
    The "default" method for performing a search. Runs a certain number of
    iterations according to the full set of policies provided.
    '''

    def __init__(self, policies):
        self.policies = policies

    def __call__(self, root, iter=100, *args, **kwargs):
        self.policies.initialize(root)
        start_time = timeit.default_timer()
        for i in xrange(iter):
            self.policies.explore(root)
        path = self.policies.extract(root)

        elapsed = timeit.default_timer() - start_time
        return elapsed, path


class RandomSearch(AbstractSearch):

    '''
    Randomly explore the task tree.
    '''

    def __init__(self, policies, instantiate=True):
        self.policies = policies
        self.instantiate = instantiate

    def __call__(self, root, *args, **kwargs):
        start_time = timeit.default_timer()
        node = root
        path = []
        while True:
            path.append(node)
            action, condition = self.policies.sample(node)
            if action is not None:
                node.children.append(Node(action=action))
                child = node.children[-1]
                if self.instantiate:
                    node.instantiate(child)
                if self.policies._initialize:
                    self.policies._initialize(child)
                node = child

        elapsed = timeit.default_timer() - start_time
        return elapsed, path


class RandomSearchNoExecution(RandomSearch):

    '''
    Randomly explore the task tree without advancing the world state -- just
    generate a list of actions to perform.
    '''

    def __init__(self, policies):
        super(RandomSearchNoExecution, self).__init__(policies,
                                                      instantiate=False)
        self.policies = policies
