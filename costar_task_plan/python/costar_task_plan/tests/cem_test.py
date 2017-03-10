#!/usr/bin/env python

import numpy as np

from costar_task_plan.trainers import CemTrainer
from costar_task_plan.gym import PointEnv

def get_weights(model):
    return model

def construct(model, weights):
    return weights

def predict(model, state):
    return model

def callback(data, reward, count):
  print "===================="
  print data
  print reward
  print count

def test(center, guess):
  env = PointEnv(np.array(center))
  trainer = CemTrainer(env,
      initial_model=np.array(guess),
      noise=1e-1,
      rollouts=25,
      learning_rate=0.5,
      callback=callback,
      get_weights_fn=get_weights,
      construct_fn=construct,
      predict_fn=predict,)
  trainer.compile()
  trainer.train()

if __name__ == '__main__':
  test([0,0],[0,0])
