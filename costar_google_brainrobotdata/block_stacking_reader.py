
import h5py
import os
import io
import glob
from PIL import Image

import numpy as np
import json
from tensorflow import keras


class CostarBlockStackingSequence(keras.utils.Sequence):
    '''Generates a batch of data from the stacking dataset.
    '''
    def __init__(self, list_IDs, batch_size=32, shuffle=True, seed = 0):
        '''Initialization
        
        #Arguments
        
        list_Ids: a list of file paths to be read
        batch_size: specifies the size of each batch
        shuffle: boolean to specify shuffle after each epoch
        '''
        self.batch_size = batch_size
        self.list_IDs = list_IDs
        self.shuffle = shuffle
        self.seed = seed
        self.on_epoch_end()

    def __len__(self):
        'Denotes the number of batches per epoch'
        return int(np.floor(len(self.list_IDs) / self.batch_size))

    def __getitem__(self, index):
        'Generate one batch of data'
        # Generate indexes of the batch
        indexes = self.indexes[index*self.batch_size:(index+1)*self.batch_size]
        print(indexes)

        # Find list of IDs
        list_IDs_temp = [self.list_IDs[k] for k in indexes]

        # Generate data
        X, y = self.__data_generation(list_IDs_temp)

        return X, y

    def on_epoch_end(self):
        #Updates indexes after each epoch
        self.indexes = np.arange(len(self.list_IDs))
        if self.shuffle == True:
            np.random.shuffle(self.indexes)

    def __data_generation(self, list_Ids):
        """ Generates data containing batch_size samples

        # Arguments

        list_Ids: a list of file paths to be read
        """

        def JpegToNumpy(jpeg):
            stream = io.BytesIO(jpeg)
            im = Image.open(stream)
            return np.asarray(im, dtype=np.uint8)

        def ConvertImageListToNumpy(data, format='numpy', data_format='NHWC'):
            """ Convert a list of binary jpeg or png files to numpy format.

            # Arguments

            data: a list of binary jpeg images to convert
            format: default 'numpy' returns a 4d numpy array,
                'list' returns a list of 3d numpy arrays
            """
            length = len(data)
            imgs = []
            for raw in data:
                img = JpegToNumpy(raw)
                if data_format == 'NCHW':
                    img = np.transpose(img, [2, 0, 1])
                imgs.append(img)
            if format == 'numpy':
                imgs = np.array(imgs)
            return imgs
        # Initialization
        X = []
        init_images = []
        current_images = []
        poses = []
        y = []
        action_labels = []
        np.random.seed(self.seed)

        # Generate data
        for i, ID in enumerate(list_Ids):
            # Store sample
            #X[i,] = np.load('data/' + ID + '.npy')
            x = ()
            data = h5py.File(ID, 'r')
            rgb_images = list(data['image'])
            rgb_images = ConvertImageListToNumpy(np.squeeze(rgb_images), format='numpy')
            #indices = [0]
            indices = [0] + list(np.random.randint(1,len(rgb_images),1))
            init_images.append(rgb_images[0])
            current_images.append(rgb_images[indices[1:]])
            poses.append(np.array(data['pose'][indices[1:]])[0]) 
            # x = x + tuple([rgb_images[indices]])
            # x = x + tuple([np.array(data['pose'])[indices]])
            for j in indices[1:]:
                action = np.zeros(41)
                action[data['gripper_action_label'][j]] = 1
                action_labels.append(action)
            # action_labels = np.array(action_labels)
            

            #print(action_labels)
            # x = x + tuple([action_labels])
            #X.append(x)
            # action_labels = np.unique(data['gripper_action_label'])
            # print(np.array(data['labels_to_name']).shape)
            #X.append(np.array(data['pose'])[indices])

            # Store class
            label = ()
            #change to goals computed
            goal_ids = np.array(data['gripper_action_goal_idx'])[indices[1:]]
            label = label + tuple(np.array(data['pose'])[goal_ids])
            #print(type(label))
            # for items in list(data['all_tf2_frames_from_base_link_vec_quat_xyzxyzw_json'][indices]):
            #     json_data = json.loads(items.decode('UTF-8'))
            #     label = label + tuple([json_data['gripper_center']])
            #     print(np.array(json_data['gripper_center']))
                #print(json_data.keys())
                #y.append(np.array(json_data['camera_rgb_frame']))
            y.append(label)
        action_labels,init_images, current_images, poses = np.array(action_labels), np.array(init_images), np.array(current_images), np.array(poses)
        poses = np.concatenate([poses,action_labels],axis = 1)
        X = (init_images, current_images, poses)
        y = np.array(y)

        return X, y

if __name__ == "__main__":
    filenames = glob.glob(os.path.expanduser("~/JHU/LAB/Projects/costar_task_planning_stacking_dataset_v0.1/*success.h5f"))
    #print(filenames)
    training_generator = CostarBlockStackingSequence(filenames,batch_size=2)
    X,y=training_generator.__getitem__(1)
    #print(X.keys())
    print(len(X))
    print(X[0].shape)
    print(y[0])
