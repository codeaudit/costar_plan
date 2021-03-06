from __future__ import print_function

import keras.backend as K
import keras.losses as losses
import keras.optimizers as optimizers
import numpy as np

from keras.callbacks import ModelCheckpoint
from keras.layers.advanced_activations import LeakyReLU
from keras.layers import Input, RepeatVector, Reshape
from keras.layers import UpSampling2D, Conv2DTranspose
from keras.layers import BatchNormalization, Dropout
from keras.layers import Dense, Conv2D, Activation, Flatten
from keras.layers.embeddings import Embedding
from keras.layers.merge import Concatenate
from keras.losses import binary_crossentropy
from keras.models import Model, Sequential
from keras.optimizers import Adam
from matplotlib import pyplot as plt

from .abstract import *
from .husky_callbacks import *
from .multi_hierarchical import *
from .robot_multi_models import *
from .mhp_loss import *
from .multi_sampler import *


class HuskyRobotMultiPredictionSampler(RobotMultiPredictionSampler):

    '''
    This class is set up as a SUPERVISED learning problem -- for more
    interactive training we will need to add data from an appropriate agent.
    '''

    def __init__(self, taskdef, *args, **kwargs):
        '''
        As in the other models, we call super() to parse arguments from the
        command line and set things like our optimizer and learning rate.
        '''
        super(HuskyRobotMultiPredictionSampler, self).__init__(taskdef, *args, **kwargs)

        self.num_pose_vars = 6
        self.num_options = 6
        self.PredictorCb = HuskyPredictorShowImage
        self.num_features = 3 


    def _makePredictor(self, features):
 
        (images, pose) = features
        img_shape = images.shape[1:]
        pose_size = pose.shape[-1]
        image_size = 1
        for dim in img_shape:
            image_size *= dim
        image_size = int(image_size)    

        if self.use_prev_option:
            enc_options = self.num_options
        else:
            enc_options = None

        ins, enc, skips, robot_skip = GetEncoder(img_shape,
                [pose_size],
                self.img_col_dim,
                dropout_rate=self.dropout_rate,
                filters=self.img_num_filters,
                leaky=False,
                dropout=True,
                pre_tiling_layers=self.extra_layers,
                post_tiling_layers=self.steps_down,
                stride1_post_tiling_layers=self.encoder_stride1_steps,
                pose_col_dim=self.pose_col_dim,
                kernel_size=[5,5],
                dense=self.dense_representation,
                batchnorm=True,
                tile=True,
                flatten=False,
                option=enc_options,
                use_spatial_softmax=self.use_spatial_softmax,
                output_filters=self.tform_filters,
                config="mobile"
                )

        if self.use_prev_option:
            img_in, pose_in, option_in = ins
        else:
            img_in, pose_in= ins
        if self.use_noise:
            z = Input((self.num_hypotheses, self.noise_dim))

        # =====================================================================
        # Create the decoders for image, arm, gripper.
        decoder = GetImagePoseDecoder(
                        self.img_col_dim,
                        img_shape,
                        dropout_rate=self.decoder_dropout_rate,
                        dense_size=self.combined_dense_size,
                        kernel_size=[3,3],
                        filters=self.img_num_filters,
                        stride2_layers=self.steps_up,
                        stride1_layers=self.extra_layers,
                        stride2_layers_no_skip=self.steps_up_no_skip,
                        tform_filters=self.tform_filters,
                        num_options=self.num_options,
                        pose_size=pose_size,
                        dropout=self.hypothesis_dropout,
                        upsampling=self.upsampling_method,
                        leaky=True,
                        dense=self.dense_representation,
                        dense_rep_size=self.img_col_dim,
                        skips=self.skip_connections,
                        robot_skip=robot_skip,
                        resnet_blocks=self.residual,
                        batchnorm=True,)


        image_outs = []
        pose_outs = []
        train_outs = []
        label_outs = []

        if self.skip_connections:
            skips.reverse()
        decoder.compile(loss="mae",optimizer=self.getOptimizer())
        decoder.summary()
        
        if not self.use_prev_option:
            option_in = Input((1,),name="prev_option_in")
            ins += [option_in]
            pv_option_in = option_in
        else:
            pv_option_in = option_in
            if self.compatibility > 0 or True:
                pv_option_in = option_in
            else:
                pv_option_in = None
        next_option_in = Input((self.num_options,),name="next_option_in")
        ins += [next_option_in]

        if self.compatibility > 0:
            value_out, next_option_out = GetNextOptionAndValue(enc,
                                                               self.num_options,
                                                               self.combined_dense_size,
                                                               option_in=pv_option_in)
        else:
            value_out, next_option_out = GetNextOptionAndValue(enc,
                                                               self.num_options,
                                                               self.value_dense_size,
                                                               option_in=pv_option_in)

        # =====================================================================
        # Create many different image decoders
        stats = []
        if self.always_same_transform:
            transform = self._getTransform(0)
        for i in range(self.num_hypotheses):
            if not self.always_same_transform:
                transform = self._getTransform(i)

            if i == 0:
                transform.summary()
            if self.use_noise:
                zi = Lambda(lambda x: x[:,i], name="slice_z%d"%i)(z)
                if self.use_next_option:
                    x = transform([enc, zi, next_option_in])
                else:
                    x = transform([enc, zi])
            else:
                if self.use_next_option:
                    x = transform([enc, next_option_in])
                else:
                    x = transform([enc])
            
            if self.sampling:
                x, mu, sigma = x
                stats.append((mu, sigma))

            # This maps from our latent world state back into observable images.
            if self.skip_connections:
                decoder_inputs = [x] + skips
            else:
                decoder_inputs = [x]

            img_x, pose_x, label_x = decoder(decoder_inputs)

            # Create the training outputs
            train_x = Concatenate(axis=-1,name="combine_train_%d"%i)([
                            Flatten(name="flatten_img_%d"%i)(img_x),
                            pose_x,
                            label_x])
            img_x = Lambda(
                    lambda x: K.expand_dims(x, 1),
                    name="img_hypothesis_%d"%i)(img_x)
            pose_x = Lambda(
                    lambda x: K.expand_dims(x, 1),
                    name="arm_hypothesis_%d"%i)(pose_x)
            label_x = Lambda(
                    lambda x: K.expand_dims(x, 1),
                    name="label_hypothesis_%d"%i)(label_x)
            train_x = Lambda(
                    lambda x: K.expand_dims(x, 1),
                    name="flattened_hypothesis_%d"%i)(train_x)

            image_outs.append(img_x)
            pose_outs.append(pose_x)
            label_outs.append(label_x)
            train_outs.append(train_x)


        image_out = Concatenate(axis=1)(image_outs)
        pose_out = Concatenate(axis=1)(pose_outs)
        label_out = Concatenate(axis=1)(label_outs)
        train_out = Concatenate(axis=1,name="all_train_outs")(train_outs)

        #next_option_out, p_h = GetHypothesisProbability(enc,
        #        self.num_hypotheses,
        #        self.num_options,
        #        label_out,
        #        self.combined_dense_size,
        #        kernel_size=None,)

        # =====================================================================
        # Create models to train
        if self.use_noise:
            ins += [z]
        predictor = Model(ins,
                [image_out, pose_out, label_out, next_option_out,
                    value_out])
        actor = None
        losses = [MhpLossWithShape(
                        num_hypotheses=self.num_hypotheses,
                        outputs=[image_size, pose_size, self.num_options],
                        weights=[0.7, 1.0, 0.1],
                        loss=["mae","mae","categorical_crossentropy"],
                        stats=stats,
                        avg_weight=0.05),
                    "binary_crossentropy",]
        loss_weights = [0.99, 0.01]
        if self.success_only:
            #outs = [train_out, next_option_out, value_out]
            outs = [train_out, next_option_out]
            #losses += ["binary_crossentropy"]
            #loss_weights += [0.01]
        else:
            outs = [train_out, value_out]

        train_predictor = Model(ins, outs)

        # =====================================================================
        # Create models to train
        train_predictor.compile(
                loss=losses,
                loss_weights=loss_weights,
                optimizer=self.getOptimizer())
        predictor.compile(loss="mae", optimizer=self.getOptimizer())
        train_predictor.summary()

        return predictor, train_predictor, actor

    def _makeModel(self, image, pose, *args, **kwargs):
        '''
        Little helper function wraps makePredictor to consturct all the models.

        Parameters:
        -----------
        image, arm, gripper: variables of the appropriate sizes
        '''
        self.predictor, self.train_predictor, self.actor = \
            self._makePredictor(
                (image, pose))
        if self.train_predictor is None:
            raise RuntimeError('did not make trainable model')

    def _makeTrainTarget(self, I_target, q_target, o_target):
        length = I_target.shape[0]
        image_shape = I_target.shape[1:]
        image_size = 1
        for dim in image_shape:
            image_size *= dim
        image_size = int(image_size)
        Itrain = np.reshape(I_target,(length, image_size))
        return np.concatenate([Itrain, q_target,o_target],axis=-1)

    def _getAllData(self, image, pose, action, label,
            prev_label, goal_image, goal_pose, value, *args, **kwargs):
        I = image / 255.
        q = pose
        qa = action
        oin = prev_label
        I_target = goal_image / 255.
        q_target = goal_pose
        o_target = label

        # Preprocess values
        value_target = np.array(value > 1.,dtype=float)
        #qa /= np.pi KDK: TODO VERIFY

        o_target = np.squeeze(self.toOneHot2D(o_target, self.num_options))
        train_target = self._makeTrainTarget(
                I_target,
                q_target,
                o_target)

        return [I, q, oin, q_target], [
                np.expand_dims(train_target, axis=1),
                o_target,
                value_target,
                np.expand_dims(qa, axis=1),
                I_target]


    def _getData(self, image, pose, action, *args, **kwargs):
        features, targets = self._getAllData(*args, **kwargs)
        tt, o1, v, qa, I = targets
        if self.use_noise:
            noise_len = features[0].shape[0]
            z = np.random.random(size=(noise_len,self.num_hypotheses,self.noise_dim))
            if self.success_only:
                return features[:self.num_features] + [o1, z], [tt, o1]
            else:
                return features[:self.num_features] + [o1, z], [tt, v]
        else:
            if self.success_only:
                
                return features[:self.num_features] + [o1], [tt, o1]
            else:
                
                return features[:self.num_features] + [o1], [tt, v]
