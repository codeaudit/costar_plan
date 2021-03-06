from costar_task_plan.abstract import AbstractReward

from tf_conversions import posemath as pm

import numpy as np

import sys


class EuclideanReward(AbstractReward):

    '''
    Distance based purely on euclidean distance to object
    '''
    
    

    def __init__(self, goal):
        '''
        Goal is an object to approach
        '''
        self.goal = goal
        self.prev_distance = sys.maxint

    def evaluate(self, world):
        '''
        Reward is 0 at object.
        '''
        robot_actor = world.actors[0]
        T_ee = pm.fromMatrix(robot_actor.robot.fwd(robot_actor.state.arm))
        T_obj = world.getObject(self.goal).state.T
        dist = (T_obj.p - T_ee.p).Norm()
        
        #print "prev distance " + str(self.prev_distance) + " new distance " + str(dist)
        
        #print dist
        reward = 1/dist
        #print reward

        #if (dist < self.prev_distance):
        #    reward = +1
        #else:
        #    reward = -1
            
        #if dist < .05:
        #    print "reached target"
        #    reward = 100
            
        #print "reward " + str(reward) 
        
        #raw_input("Press Enter to continue...")
        
        self.prev_distance = dist
        
        return reward,0
