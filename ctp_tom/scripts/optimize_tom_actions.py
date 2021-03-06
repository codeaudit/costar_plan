#!/usr/bin/env python

# By Chris Paxton
# (c) 2017 The Johns Hopkins University
# See License for more details

from tom_oranges import MakeTomTaskModel, OrangesTaskArgs, OrangesDefaultTaskArgs

from costar_task_plan.abstract import AbstractReward, AbstractFeatures
from costar_task_plan.mcts import ContinuousSamplerTaskPolicies, Node
from costar_task_plan.mcts import MonteCarloTreeSearch
from costar_task_plan.mcts import ContinuousTaskSample
from costar_task_plan.robotics.core import *
from costar_task_plan.robotics.tom import TomWorld, OpenLoopTomExecute, ParseTomArgs
from costar_task_plan.tools import showTask, OptimizePolicy
from std_srvs.srv import Empty as EmptySrv

import argparse
import rospy

def load_tom_world(regenerate_models):
    world = TomWorld('./',load_dataset=regenerate_models)
    if regenerate_models:
        world.saveModels('tom')
    return world

if __name__ == '__main__':
    '''
    Main function:
     - create a TOM world
     - verify that the data is being managed correctly
     - fit models to data (optional)
     - create Reward objects as appropriate
     - create Policy objects as appropriate
    '''

    import signal
    signal.signal(signal.SIGINT, exit)

    test_args = ParseTomArgs()

    try:
      rospy.init_node('tom_test_node')
      world = load_tom_world(test_args.regenerate_models)
    except RuntimeError, e:
      print "Failed to create world. Are you in the right directory?"
      raise e

    # Set up the task model
    task = MakeTomTaskModel(world.lfd)
    args = OrangesDefaultTaskArgs()
    filled_args = task.compile(args)
    execute = True

    for obj_class, names in args.items():
        for name in names:
            world.addObject(name, obj_class)

    # Run the policy optimization loop
    policies = ContinuousSamplerTaskPolicies(task)
    OptimizePolicy(world, policies)

