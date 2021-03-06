'''
By Chris Paxton
Copyright (c) 2017, The Johns Hopkins University
All rights reserved.

This license is for non-commercial use only, and applies to the following
people associated with schools, universities, and non-profit research institutions

Redistribution and use in source and binary forms by the aforementioned
people and institutions, with or without modification, are permitted
provided that the following conditions are met:

* Usage is non-commercial.

* Redistribution should be to the listed entities only.

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
from __future__ import print_function

from abstract import AbstractAgent
from costar_task_plan.mcts import ContinuousSamplerTaskPolicies
from costar_task_plan.mcts import Node, OptionsExecutionManager

import numpy as np

class TaskAgent(AbstractAgent):
    '''
    This agent uses a task model to generate a random sequence of actions. It
    requires a compiled task model (associated with the environment) for
    execution.

    An "instantiated task model" outlines a set of short-running policies that
    will take the robot towards its goals. This will use the "sample" function
    associated with each stage in the task plan to generate stochastic
    executions.
    '''
    
    NUM_REPEATS = 1
    name = "random"

    def __init__(self, *args, **kwargs):
        super(TaskAgent, self).__init__(*args, **kwargs)

    def _fit(self, num_iter):
        '''
        This is a "fake" agent -- it does not fit any model in particular, it
        just generates some data. You almost certainly just want to call fit()
        to generate training data that can be used with some other options.
        '''

        task = self.env.taskModel()
        if not task.compiled:
            raise RuntimeError('environment must have associated compiled task model!')

        for i in xrange(num_iter):

            # Initialize random number generator so we get consistent results
            # when generating levels. This lets us more easily debug problems
            # with task models and with learned policies.
            if self.seed is not None:
                np.random.seed(int((self.seed+i)/self.NUM_REPEATS))

            print("---- Iteration %d ----"%(i+1))
            self.env.reset()

            # Make sure that we explore the environment a different way
            if self.seed is not None:
                seed = int(self.seed+i)
                np.random.seed(seed)
            else:
                seed = None

            names, options = task.sampleSequence()
            plan = OptionsExecutionManager(options)

            while not self._break:
                control = plan.apply(self.env.world)
                features, reward, done, info = self.env.step(control)
                if control is not None and control.error:
                    print("Error following selected policy action!")
                    reward -= 100
                    done = True
                idx = plan.idx
                if idx >= len(names):
                    # We reached the end of the task plan and were not
                    # successful -- this indicates that we failed for some
                    # reason, and we should not just sit here waiting to see
                    # what happens.
                    idx = len(names) - 1
                    reward -= 100
                    done = True
                else:
                    print(idx,task.index(names[idx]),names[idx])
                    self._addToDataset(self.env.world,
                            control,
                            features,
                            reward,
                            done,
                            i,
                            task.index(names[idx]),
                            task.numIndices(),
                            seed=seed)
                if done:
                    break

            if self._break:
                return

