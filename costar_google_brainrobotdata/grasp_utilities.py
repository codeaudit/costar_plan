import sys
import re
import numpy as np
import os
import json
import datetime


def rotate(data, shift=1):
    """ Rotates indices up 1 for a list or numpy array.

    For example, [0, 1, 2] will become [1, 2, 0] and
    [4, 3, 1, 0] will become [3, 1, 0, 4].
    The contents of index 0 becomes the contents of index 1,
    and the final entry will contain the original contents of index 0.
    Always operates on axis 0.
    """
    if isinstance(data, list):
        return data[shift:] + data[:shift]
    else:
        return np.roll(data, shift, axis=0)


def mkdir_p(path):
    """Create the specified path on the filesystem like the `mkdir -p` command

    Creates one or more filesystem directory levels as needed,
    and does not return an error if the directory already exists.
    """
    # http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def timeStamped(fname, fmt='%Y-%m-%d-%H-%M-%S_{fname}'):
    """ Apply a timestamp to the front of a filename description.

    see: http://stackoverflow.com/a/5215012/99379
    """
    return datetime.datetime.now().strftime(fmt).format(fname=fname)


def load_hyperparams_json(hyperparams_file, fine_tuning=False, learning_rate=None, feature_combo_name=None):
    """ Load hyperparameters from a json file

    # Returns

    Hyperparams
    """
    kwargs = {}
    hyperparams = None
    if hyperparams_file is not None and hyperparams_file:
        with open(hyperparams_file, mode='r') as hyperparams:
            kwargs = json.load(hyperparams)
            hyperparams = kwargs
    if fine_tuning:
        kwargs['trainable'] = True
        kwargs['learning_rate'] = learning_rate
        # TODO(ahundt) should we actually write the fine tuning settings out to the hyperparams log?
        # hyperparams = kwargs

    if (kwargs is not None and feature_combo_name is not None and
            'feature_combo_name' in kwargs and
            kwargs['feature_combo_name'] != feature_combo_name):
        print('Warning: overriding old hyperparam feature_combo_name: %s'
              ' with new feature_combo_name: %s. This means the network '
              'structure and inputs will be different from what is defined '
              'in the hyperparams file: %s' %
              (kwargs['feature_combo_name'], feature_combo_name, hyperparams_file))
        kwargs.pop('feature_combo_name')
        if 'feature_combo_name' in hyperparams:
            hyperparams.pop('feature_combo_name')
    return kwargs


def is_sequence(arg):
    """Returns true if arg is a list or another Python Sequence, and false otherwise.

        source: https://stackoverflow.com/a/17148334/99379
    """
    return (not hasattr(arg, "strip") and
            hasattr(arg, "__getitem__") or
            hasattr(arg, "__iter__"))


def find_best_weights(fold_log_dir, match_string='', verbose=0, out_file=sys.stdout):
    """ Find the best weights file with val_*0.xxx out in a directory
    """
    # Now we have to load the best model
    # '200_epoch_real_run' is for backwards compatibility before
    # the fold nums were put into each fold's log_dir and run_name.
    directory_listing = os.listdir(fold_log_dir)
    fold_checkpoint_files = []
    for name in directory_listing:
        name = os.path.join(fold_log_dir, name)
        if not os.path.isdir(name) and '.h5' in name:
            if '200_epoch_real_run' in name or match_string in name:
                fold_checkpoint_files += [name]

    # check the filenames for the highest val score
    fold_checkpoint_file = None
    best_val = 0.0
    for filename in fold_checkpoint_files:
        if 'val_' in filename:
            # pull out all the floating point numbers
            # source: https://stackoverflow.com/a/4703409/99379
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", filename)
            if len(nums) > 0:
                # don't forget about the .h5 at the end...
                cur_num = np.abs(float(nums[-2]))
                if verbose > 0:
                    out_file.write('old best ' + str(best_val) + ' current ' + str(cur_num))
                if cur_num > best_val:
                    if verbose > 0:
                        out_file.write('new best: ' + str(cur_num) + ' file: ' + filename)
                    best_val = cur_num
                    fold_checkpoint_file = filename

    if fold_checkpoint_file is None:
        raise ValueError('\n\nSomething went wrong when looking for model checkpoints, '
                         'you need to take a look at model_predict_k_fold() '
                         'in cornell_grasp_train.py. Here are the '
                         'model checkpoint files we were looking at: \n\n' +
                         str(fold_checkpoint_files))
    return fold_checkpoint_file