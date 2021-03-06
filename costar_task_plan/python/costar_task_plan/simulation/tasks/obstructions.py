from abstract import AbstractTaskDefinition
from default import DefaultTaskDefinition
from costar_task_plan.simulation.world import *
from costar_task_plan.simulation.option import *
from costar_task_plan.simulation.reward import *
from costar_task_plan.simulation.condition import *

import numpy as np
import os
import pybullet as pb
import rospkg


class ObstructionsTaskDefinition(DefaultTaskDefinition):

    '''
    Define a simple task. The robot needs to pick up and stack blocks of
    different colors in a particular order.
    '''

    # define object filenames
    list_of_models_to_manipulate = [
        'c_clamp', 'drill_blue_small', 'driller_point_metal',
        'driller_small', 'keyboard', 'mallet_ball_pein',
        'mallet_black_white', 'mallet_drilling', 'mallet_fiber',
        'mug', 'old_hammer', 'pepsi_can', 'sander']
    models = set(list_of_models_to_manipulate)
    spawn_pos_min = np.array([-0.4, -0.25, 0.1])
    spawn_pos_max = np.array([-0.65, 0.25, 0.3])
    spawn_pos_delta = spawn_pos_max - spawn_pos_min
    
    block_urdf = "%s.urdf"
    model = "block"
    blocks = ["red", "blue", "yellow", "green"]

    # Objects are placed into a random stack.
    stack_pos = [
        # np.array([-0.5, 0., 0.]),
        np.array([-0.5, 0.1, 0.]),
        np.array([-0.5, 0.2, 0.]),
        np.array([-0.5, -0.1, 0.]),
        np.array([-0.5, -0.2, 0.]),
    ]

    over_final_stack_pos = np.array([-0.5, 0., 0.5])
    final_stack_pos = np.array([-0.5, 0., 0.05])
    grasp_q = (-0.27, 0.65, 0.65, 0.27)

    def __init__(self, stage, *args, **kwargs):
        '''
        Read in arguments defining how many blocks to create, where to create
        them, and the size of the blocks. Size is given as mean and covariance,
        blocks are placed at random.
        '''
        super(ObstructionsTaskDefinition, self).__init__(*args, **kwargs)
        self.stage = stage
        self.block_ids = []

    def _makeTask(self):
        AlignOption = lambda goal: GoalDirectedMotionOption(
            self.world,
            goal,
            pose=((0.05, 0, 0.05), self.grasp_q),
            pose_tolerance=(0.025, 0.025),
            joint_velocity_tolerance=0.05,)
        align_args = {
            "constructor": AlignOption,
            "args": ["block"],
            "remap": {"block": "goal"},
        }
        GraspOption = lambda goal: GoalDirectedMotionOption(
            self.world,
            goal,
            pose=((0.0, 0, 0.0), self.grasp_q),
            pose_tolerance=(0.025, 0.025),
            joint_velocity_tolerance=0.05,)
        grasp_args = {
            "constructor": GraspOption,
            "args": ["block"],
            "remap": {"block": "goal"},
        }
        LiftOption = lambda: GeneralMotionOption(
            pose=(self.over_final_stack_pos, self.grasp_q),
            pose_tolerance=(0.025, 0.025),
            joint_velocity_tolerance=0.05,)
        lift_args = {
            "constructor": LiftOption,
            "args": []
        }
        PlaceOption = lambda: GeneralMotionOption(
            pose=(self.final_stack_pos, self.grasp_q),
            pose_tolerance=(0.025, 0.025),
            joint_velocity_tolerance=0.05,)
        place_args = {
            "constructor": PlaceOption,
            "args": []
        }
        close_gripper_args = {
            "constructor": CloseGripperOption,
            "args": []
        }
        open_gripper_args = {
            "constructor": OpenGripperOption,
            "args": []
        }

        # Create a task model
        task = Task()
        task.add("align", None, align_args)
        task.add("grasp", "align", grasp_args)
        task.add("close_gripper", "grasp", close_gripper_args)
        task.add("lift", "close_gripper", lift_args)
        task.add("place", "lift", place_args)
        task.add("open_gripper", "place", open_gripper_args)
        task.add("done", "open_gripper", lift_args)

        return task

    def _addTower(self, pos, blocks, urdf_dir):
        '''
        Helper function that generats a tower containing listed blocks at the
        specific position
        '''
        z = 0.025
        ids = []
        for block in blocks:
            urdf_filename = os.path.join(
                urdf_dir, self.model, self.block_urdf % block)
            obj_id = pb.loadURDF(urdf_filename)
            pb.resetBasePositionAndOrientation(
                obj_id,
                (pos[0], pos[1], z),
                (0, 0, 0, 1))
            self.addObject("block", "%s_block" % block, obj_id)
            z += 0.05
            ids.append(obj_id)
        return ids

    def _setup(self):
        '''
        Create task by adding objects to the scene
        '''

        rospack = rospkg.RosPack()
        path = rospack.get_path('costar_objects')
        urdf_dir = os.path.join(path, self.urdf_dir)
        sdf_dir = os.path.join(path, self.sdf_dir)
        objs = [obj for obj in os.listdir(
            sdf_dir) if os.path.isdir(os.path.join(sdf_dir, obj))]

        randn = np.random.randint(1, len(objs))

        objs_name_to_add = np.random.choice(objs, randn)
        objs_to_add = [os.path.join(sdf_dir, obj, self.model_file_name)
                       for obj in objs_name_to_add]

        identity_orientation = pb.getQuaternionFromEuler([0, 0, 0])
        # load sdfs for all objects and initialize positions
        for obj_index, obj in enumerate(objs_to_add):
            if objs_name_to_add[obj_index] in self.models:
                try:
                    print 'Loading object: ', obj
                    obj_id_list = pb.loadSDF(obj)
                    for obj_id in obj_id_list:
                        self.objs.append(obj_id)
                        random_position = np.random.rand(
                            3) * self.spawn_pos_delta + self.spawn_pos_min
                        pb.resetBasePositionAndOrientation(
                            obj_id, random_position, identity_orientation)
                except Exception, e:
                    print e

        
        placement = np.array(range(len(self.stack_pos)))
        np.random.shuffle(placement)
        for i, pos in enumerate(self.stack_pos):
            blocks = []
            for idx, block in zip(placement, self.blocks):
                if idx == i:
                    blocks.append(block)
            ids = self._addTower(pos, blocks, urdf_dir)
            self.block_ids += ids

        self.world.addCondition(JointLimitViolationCondition(), -100,
                                "joints must stay in limits")
        self.world.addCondition(TimeCondition(10.), -100, "time limit reached")
        self.world.reward = EuclideanReward("red_block")

        # =====================================================================
        # Set up the "first stage" of the tower -- so that we only need to
        # correctly place a single block.
        # NOTE: switching to give positive rewards for all to make it easier to
        # distinguish good training data from bad.
        if self.stage == 0:
            threshold = 0.035
            self.world.addCondition(
                ObjectAtPositionCondition("red_block",
                                          self.final_stack_pos, threshold),
                100,
                "block in right position")
            self.world.addCondition(
                ObjectAtPositionCondition("blue_block",
                                          self.final_stack_pos,
                                          threshold),
                50,
                "wrong block")
            self.world.addCondition(
                ObjectAtPositionCondition("green_block",
                                          self.final_stack_pos,
                                          threshold),
                50,
                "wrong block")
            self.world.addCondition(
                ObjectAtPositionCondition("yellow_block",
                                          self.final_stack_pos,
                                          threshold),
                50,
                "wrong block")

    def reset(self):
        '''
        Reset blocks to new random towers. Also resets the world and the
        configuration for all of the new objects, including the robot.
        '''

        # placement = np.random.randint(
        #        0,
        #        len(self.stack_pos),
        #        (len(self.blocks),))
        placement = np.array(range(len(self.stack_pos)))
        np.random.shuffle(placement)
        self.world.done = False
        self.world.ticks = 0

        # loop over all stacks
        # pull out ids now associated with a stack
        for i, pos in enumerate(self.stack_pos):
            blocks = []
            for idx, block in zip(placement, self.block_ids):
                    if idx == i:
                        blocks.append(block)

            # add blocks to tower
            z = 0.025
            for block_id in blocks:
                pb.resetBasePositionAndOrientation(
                    block_id,
                    (pos[0], pos[1], z),
                    (0, 0, 0, 1))
                z += 0.05

        self._setupRobot(self.robot.handle)

    def getName(self):
        return "obstructions"
