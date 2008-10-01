#! /usr/bin/env python2.5
# -*- coding: utf-8 -*-

import doctest
import math
import random
import sys

from math import log

import scipy

from arac.pybrainbridge import _FeedForwardNetwork
from pybrain.datasets import SupervisedDataSet
from pybrain.rl.environments.functions import FunctionEnvironment
from pybrain.structure import MdrnnLayer, LinearLayer, IdentityConnection, \
    SigmoidLayer
from pybrain.rl.learners.blackboxoptimizers.fem import FEM
from pybrain.rl.learners.blackboxoptimizers.cmaes import CMAES
from pybrain.rl.learners.blackboxoptimizers.neldermead import NelderMead


class Shape(object):
    
    def makeArray(self, shape):
        width, height = shape
        arr = scipy.empty(shape)
        for x in xrange(width):
            for y in xrange(height):
                arr[x, y] = 1. if self.contains(x, y) else 0.
        return arr
            

class Circle(Shape):
    
    def __init__(self, center, radius):
        self.center = center
        self.radiusSquared = radius**2
        
    def contains(self, x, y):
        return x**2 + y**2 <= self.radiusSquared
        
    @classmethod
    def random(cls, maxwidth, maxheight):
        radius = (random.random() * min(maxwidth, maxheight))
        center = scipy.array((random.random() * maxwidth, 
                              random.random() * maxheight))
        return cls(center, radius)
        
        
class Rectangle(Shape):

    def __init__(self, topleft, bottomright):
        self.topleft = topleft
        self.bottomright = bottomright

    def contains(self, x, y):
        """Tell if a point (x, y) is in the rectangle.
        
        >>> r = Rectangle((0, 2), (5, 6))
        >>> r.contains(0, 2)
        True
        >>> r.contains(-1, 3)
        False
        >>> r.contains(1, 3)
        True
        """
        return (x >= self.topleft[0] and
                y >= self.topleft[1] and
                x <= self.bottomright[0] and
                y <= self.bottomright[1])
                   
    @classmethod
    def random(cls, maxwidth, maxheight):
        v1, v2 = random.random() * maxwidth, random.random() * maxwidth
        v1, v2 = (v1, v2) if v1 < v2 else (v2, v1)
        h1, h2 = random.random() * maxheight, random.random() * maxheight
        h1, h2 = (h1, h2) if h1 < h2 else (h2, h1)
        
        return cls((int(v1), int(h1)), (int(v2), int(h2)))
        
        
class CirclectDataSet(SupervisedDataSet):

    def __init__(self, width=25, height=25, amount_per_class=100):
        super(CirclectDataSet, self).__init__(width * height, 2)
        self.width = width
        self.height = height
        points = [(x, y) for x in xrange(self.width)
                         for y in xrange(self.height)]
        for _ in xrange(amount_per_class):
            circle = Circle.random(self.width, self.height)
            rect = Rectangle.random(self.width, self.height)
            item = circle.makeArray((self.width, self.height))
            self.addSample(item.flatten(), [0.2, 0.8])
            item = rect.makeArray((self.width, self.height))
            self.addSample(item.flatten(), [0.8, 0.2])   


class MdrnnCirclet(FunctionEnvironment):
    
    def __init__(self, width, height, dataset):
        self.width = width
        self.height= height
        self.dataset = dataset
        
        # Initialize MDRNN
        self.net = _FeedForwardNetwork()
        inlayer = LinearLayer(width * height)
        hiddenlayer = MdrnnLayer(timedim=2, 
                                 shape=(width, height), 
                                 blockshape=(1, 1), 
                                 hiddendim=4,
                                 outsize=2,
                                 name='mdrnn')

        outlayer = SigmoidLayer(width * height * 2)
        con1 = IdentityConnection(inlayer, hiddenlayer)
        con2 = IdentityConnection(hiddenlayer, outlayer)
        self.net.addInputModule(inlayer)
        self.net.addModule(hiddenlayer)
        self.net.addOutputModule(outlayer)
        self.net.addConnection(con1)
        self.net.addConnection(con2)

        self.net.sortModules()
    
    def f(self, x):
        self.net['mdrnn'].params[:] = x
        correct_answers_A = 0
        correct_answers_B = 0
        error = 0
        for (inpt, target_vec) in self.dataset:
            # print inpt
            output = self.net.activate(inpt)
            indic = output.reshape(self.width * self.height, 2).sum(axis=0)
            klass = indic.argmax()
            target = target_vec.argmax()
            if klass == target == 0:
                correct_answers_A += 1
            elif klass == target == 1:
                correct_answers_B += 1
            diff = output - target
            error += scipy.inner(diff, diff)
            # print error
            # print indic
            # print target, klass
        print "%i/%i" % (correct_answers_A, correct_answers_B)
        print error / len(self.dataset)
        return error / len(self.dataset)
            
if __name__ == '__main__':
    f, _ = doctest.testmod()
    if f > 0:
        sys.exit()
    
    scipy.random.seed(0)
    width = 10
    height = 10
    ds = CirclectDataSet(width, height, 100)
    mdrnn_env = MdrnnCirclet(width, height, ds)
    print scipy.size(mdrnn_env.net['mdrnn'].params)
    optimizer = CMAES(mdrnn_env, mdrnn_env.net['mdrnn'].params)
    optimizer.minimize = True
    optimizer.verbose = True
    # optimizer.elitist = True
    # optimizer.forgetFactor = 0.7
    optimizer.learn()
