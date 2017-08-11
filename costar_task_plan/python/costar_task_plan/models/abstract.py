'''
Chris Paxton
(c) 2017 Johns Hopkins University
See license for details
'''
import numpy as np

import keras.optimizers as optimizers

class AbstractAgentBasedModel(object):
    '''
    In CTP, models are trained based on output from a particular agent --
    possibly the null agent (which would just load a dataset). The Agent class
    will also provide the model with a way to collect data or whatever.
    '''

    def __init__(self, lr=1e-4, epochs=1000, iter=1000, batch_size=32,
            clipnorm=100, show_iter=0, pretrain_iter=5,
            optimizer="sgd", model_descriptor="model", zdim=16, features=None,
            task=None, robot=None, model="", *args,
            **kwargs):

        if lr == 0 or lr < 1e-30:
            raise RuntimeError('You probably did not mean to set ' + \
                               'learning rate to %f'%lr)
        elif lr > 1.:
            raise RuntimeError('Extremely high learning rate: %f' % lr)

        self.lr = lr
        self.iter = iter
        self.show_iter = show_iter
        self.pretrain_iter = pretrain_iter
        self.noise_dim = zdim
        self.epochs = epochs
        self.batch_size = batch_size
        self.optimizer = optimizer
        self.model_descriptor = model_descriptor
        self.task = task
        self.features = features
        self.robot = robot
        self.name = "%s_%s"%(model, self.model_descriptor)
        self.clipnorm = clipnorm
        if self.task is not None:
            self.name += "_%s"%self.task
        if self.features is not None:
            self.name += "_%s"%self.features
        
        # default: store the whole model here.
        # NOTE: this may not actually be where you want to save it.
        self.model = None

        print "==========================================================="
        print "Name =", self.name
        print "Features = ", self.features
        print "Robot = ", self.robot
        print "Task = ", self.task
        print "Model type = ", model
        print "Model description = ", self.model_descriptor
        print "-----------------------------------------------------------"
        print "Iterations = ", self.iter
        print "Epochs = ", self.epochs
        print "Batch size =", self.batch_size
        print "Noise dim = ", self.noise_dim
        print "Show images every %d iter"%self.show_iter
        print "Pretrain for %d iter"%self.pretrain_iter
        print "-----------------------------------------------------------"
        print "Optimizer =", self.optimizer
        print "Learning Rate = ", self.lr
        print "Clip Norm = ", self.clipnorm
        print "==========================================================="

    def train(self, agent, *args, **kwargs):
        raise NotImplementedError('train() takes an agent.')

    def save(self):
        '''
        Save to a filename determined by the "self.name" field.
        '''
        if self.model is not None:
            self.model.save_weights(self.name + ".h5f")
        else:
            raise RuntimeError('save() failed: model not found.')

    def load(self, world, *args, **kwargs):
        '''
        Load will use the current model descriptor and name to load the file
        that you are interested in, at least for now.
        '''
        control = world.zeroAction()
        reward = world.initial_reward
        features = world.computeFeatures()
        action_label = ''
        example = 0
        done = False
        data = world.vectorize(control, features, reward, done, example,
                action_label)
        kwargs = {}
        for k, v in data:
            kwargs[k] = np.array([v])
        self._makeModel(**kwargs)
        self._loadWeights()

    def _makeModel(self, *args, **kwargs):
        '''
        Create the model based on some data set shape information.
        '''
        raise NotImplementedError('_makeModel() not supported yet.')

    def _loadWeights(self, *args, **kwargs):
        '''
        Load model weights. This is the default load weights function; you may
        need to overload this for specific models.
        '''
        if self.model is not None:
            print "using " + self.name + ".h5f"
            print self.model.summary()
            #print args
            #weight_location = args.load_model.name
            #self.model.load_weights(weight_location)
            self.model.load_weights(self.name + ".h5f")
        else:
            raise RuntimeError('_loadWeights() failed: model not found.')

    def getOptimizer(self):
        '''
        Set up a keras optimizer based on whatever settings you provided.
        '''
        optimizer = optimizers.get(self.optimizer)
        try:
            optimizer.lr = self.lr
            optimizer.clipnorm = self.clipnorm
        except Exception, e:
            print e
            raise RuntimeError('asdf')
        return optimizer

    def predict(self, world):
        '''
        Implement this to predict... something... from a world state
        observation.

        Parameters:
        -----------
        world: a single world observation.
        '''
        raise NotImplementedError('predict() not supported yet.')

    def toOneHot2D(self, f, dim):
        if len(f.shape) == 1:
            f = np.expand_dims(f, -1)
        assert len(f.shape) == 2
        shape = f.shape + (dim,)
        oh = np.zeros(shape)
        #oh[np.arange(f.shape[0]), np.arange(f.shape[1]), f]
        for i in xrange(f.shape[0]):
            for j in xrange(f.shape[1]):
                oh[i,j,f[i,j]] = 1.
        return oh


class HierarchicalAgentBasedModel(AbstractAgentBasedModel):

    '''
    This version of the model will save a set of associated policies, all
    trained via direct supervision. These are:

    - transition model (x, u) --> (x'): returns next expected state
    - supervisor policy (x, o) --> (o'): returns next high-level action to take
    - control policies (x, o) --> (u): return the next action to take

    The supervisor takes in the previous labeled action, not the one currently
    being executed; it takes in 0 if no action has been performed yet.
    '''

    def __init__(self, *args, **kwargs):
        super(HierarchicalAgentBasedModel, self).__init__(*args, **kwargs)
        self.num_actions = 0
    
    def _makeSupervisor(self, feature, label, num_labels):
        '''
        This needs to create a supervisor. This one maps from input to the
        space of possible action labels.
        '''
        raise NotImplementedError('does not create supervisor yet')

    def _makePolicy(self, features, action, hidden=None):
        '''
        Create the control policy mapping from features (or hidden) to actions.
        '''
        raise NotImplementedError('does not create policy yet')

    def _makeHierarchicalModel(self, features, action, label, example, reward,
              *args, **kwargs):
        '''
        This is the helper that actually sets everything up.
        '''
        num_labels = label.shape[-1]
        assert num_labels > 1
        hidden, self.supervisor = self._makeSupervisor(features, label,
                num_labels)
        self.supervisor.summary()

        
        # Learn a baseline for comparisons and whatnot
        self.baseline = self._makePolicy(features, action, hidden)
        self.baseline.summary()

        # We assume label is one-hot. This is the same as the "baseline"
        # policy, but we learn a separate one for each high-level action
        # available to the actor.
        self.policies = []
        for i in xrange(num_labels):
            self.policies.append(self._makePolicy(features, action, hidden))
        
    def _fitSupervisor(self, features, prev_label, label):
        #self.supervisor.fit([features, prev_label], [label])
        '''
        Fit a high-level policy that tells us which low-level action we could
        be taking at any particular time.
        '''
        self.supervisor.fit([features], [label], epochs=self.epochs)

    def _fitPolicies(self, features, label, action):
        '''
        Fit different policies for each model.
        '''
        # Divide up based on label
        idx = np.argmax(np.squeeze(label[:,-1,:]),axis=-1)

        for i, model in enumerate(self.policies):
            # select data for this model
            x = features[idx==i]
            a = action[idx==i]
            if a.shape[0] == 0:
                #raise RuntimeError('no examples for %d'%i)
                print 'WARNING: no examples for %d'%i
                continue
            model.fit([x], [a], epochs=self.epochs)

    def _fitBaseline(self, features, action):
        self.baseline.fit([features], [action], epochs=self.epochs)

    def save(self):
        '''
        Save to a filename determined by the "self.name" field.
        '''
        if self.supervisor is not None:
            self.supervisor.save_weights(self.name + "_supervisor.h5f")
            for i, policy in enumerate(self.policies):
                policy.save_weights(self.name + "_policy%02d.h5f"%i)
        else:
            raise RuntimeError('save() failed: model not found.')

    def _loadWeights(self, *args, **kwargs):
        '''
        Load model weights. This is the default load weights function; you may
        need to overload this for specific models.
        '''
        if self.model is not None:
            print "using " + self.name + ".h5f"
            print self.model.summary()
            #print args
            #weight_location = args.load_model.name
            #self.model.load_weights(weight_location)
            self.model.load_weights(self.name + ".h5f")
        else:
            raise RuntimeError('_loadWeights() failed: model not found.')

    def predict(self, world):
        '''
        This is the basic, "dumb" option. Compute the next option/policy to
        execute by evaluating the supervisor, then just call that model.
        '''
        features = world.getHistoryMatrix()
        if isinstance(features, list):
            assert len(features) == len(self.model.inputs)
        else:
            features = [features]
        if self.supervisor is None:
            raise RuntimeError('high level model is missing')
        features = [f.reshape((1,)+f.shape) for f in features]
        res = self.supervisor.predict(features)
        next_policy = np.argmax(res)

        # Retrieve the next policy we want to execute
        policy = self.policies[next_policy]

        # Evaluate this policy to get the next action out
        return policy.predict(features)

