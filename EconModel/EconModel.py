# -*- coding: utf-8 -*-
""" EconModelClass

Provides a class for economic models with methods for saving and loading
and interfacing with numba jitted functions and C++.

"""

import os
from copy import deepcopy
import pickle
from types import SimpleNamespace
from collections import namedtuple

import numpy as np

from .cpptools import link_to_cpp

# main
class EconModelClass():
    
    def __init__(self,name='',load=False,from_dict=None,skip=None,**kwargs):
        """ defines default attributes """

        if load: assert from_dict is None, 'dictionary should be be specified when loading'

        # a. name
        self.name = name

        # list of internal of attributes (used when saving)
        self.internal_attrs = [
            'savefolder','namespaces','other_attrs',
            'cpp_filename','cpp_options','cpp_structsmap']

        # b. new or load
        self.savefolder = 'saved'

        if from_dict is None: # new or load
            
            # i. empty containers
            self.namespaces = []
            self.other_attrs = []
            self.cpp = SimpleNamespace() # overwritten later, helps linter (not internal attribute)
            self.cpp_filename = None
            self.cpp_options = {}
            self.cpp_structsmap = {}

            # ii. settings
            assert hasattr(self,'settings'), 'the model must have defined an .settings() method'
            self.settings()

            # default to none
            for attr in self.other_attrs:
                if not hasattr(self,attr): setattr(self,attr,None)

            if len(self.namespaces) == 0:
                self.namespaces =  ['par','sol','sim']
                self.par = SimpleNamespace() # -> helps linter
                self.sol = SimpleNamespace() # -> helps linter
                self.sim = SimpleNamespace() # -> helps linter
            else:
                for ns in self.namespaces:
                    setattr(self,ns,SimpleNamespace())

            # iii setup
            assert hasattr(self,'setup'), 'the model must have defined an .setup() method'
            self.setup()

            if load:
                
                # iv. create
                self.allocate()
                
                # v. overwrite
                self.load(skip=skip)

                # vi. update par
                self.__update(kwargs)

            else:

                # iv. update
                self.__update(kwargs)
                
                # vi. allocate
                assert hasattr(self,'allocate'), 'the model must have defined an .allocate() method'
                self.allocate()

        else:
            
            self.from_dict(from_dict)

        # c. infrastructure
        self.infer_types()
    
    def __name__(self):
        return 'EconModelClass' 

    def __update(self,upd_dict):
        """ update """

        for nskey,values in upd_dict.items():
            assert nskey in self.namespaces, f'{nskey} is not a namespace'
            assert type(values) is dict, f'{nskey} must be dict'
            for key,value in values.items():
                assert hasattr(getattr(self,nskey),key), f'{key} is not in {nskey}' 
                setattr(getattr(self,nskey),key,value)        

    ####################
    ## infrastructure ##
    ####################

    def infer_types(self):
        """ setup infrastructure to call numba jit functions """
        
        _ns_specs = self._ns_specs = {}
        _ns_namedtuple = _ns_specs['namedtuple'] = {}
        _ns_keys = _ns_specs['keys'] = {}
        _ns_types = _ns_specs['types'] = {}
        _ns_np_dtypes = _ns_specs['np_dtypes'] = {}
        _ns_np_ndims = _ns_specs['np_ndims'] = {}

        def create_type_list(value):

            type_ = type(value)
            if type_ in [float,np.float_]:
                return [float,np.float_]
            elif type_ in [int,np.int_]:
                return [int,np.int_]                
            else:
                return [type_]

        for ns in self.namespaces:
            ns_dict = getattr(self,ns).__dict__
            _ns_namedtuple[ns] = namedtuple(f'{ns.capitalize()}Class',[key for key in ns_dict.keys()])
            _ns_keys[ns] = [key for key in ns_dict.keys()]
            _ns_types[ns] = {key:create_type_list(value) for key,value in ns_dict.items()}
            _ns_np_dtypes[ns] = {key:value.dtype for key,value in ns_dict.items() if type(value) == np.ndarray}
            _ns_np_ndims[ns] = {key:value.ndim for key,value in ns_dict.items() if type(value) == np.ndarray}

    def check_types(self):
        """ check everything is unchanged since initialization """

        for ns in self.namespaces:
            
            for key,value in getattr(self,ns).__dict__.items():
                if not key in self._ns_specs['keys'][ns]: raise ValueError(f'{key} is not allowed in .{ns}')
                allowed_types = self._ns_specs['types'][ns][key]
                if not type(value) in allowed_types: raise ValueError(f'{ns}.{key} has type {type(value)}, should be in {allowed_types}')
                if type(value) == np.ndarray:
                    allowed_dtype = self._ns_specs['np_dtypes'][ns][key]
                    allowed_ndim = self._ns_specs['np_ndims'][ns][key]
                    if not value.dtype == allowed_dtype: raise ValueError(f'{ns}.{key} has dtype {value.dtype}, should be {allowed_dtype}')
                    if not value.ndim == allowed_ndim: raise ValueError(f'{ns}.{key} has ndim {value.ndim}, should be {allowed_ndim}')

    def update_jit(self):
        """ create namedtuples for jit """

        self.check_types()

        self._ns_jit = {}
        for ns in self.namespaces:
            self._ns_jit[ns] = self._ns_specs['namedtuple'][ns](**getattr(self,ns).__dict__)

    ####################
    ## save-copy-load ##
    ####################
    
    def __all_attrs(self):
        """ return all attributes """

        return self.namespaces + self.other_attrs + self.internal_attrs

    def as_dict(self,drop=None):
        """ return a dict version of the model """
        
        drop = [] if drop is None else drop

        model_dict = {}
        for attr in self.__all_attrs():
            if not attr in drop: model_dict[attr] = getattr(self,attr)

        model_dict['link_to_cpp'] = not type(self.cpp) is SimpleNamespace

        return model_dict

    def from_dict(self,model_dict,do_copy=True):
        """ construct the model from a dict version of the model """

        self.namespaces = model_dict['namespaces']
        self.other_attrs = model_dict['other_attrs']
        for attr in self.__all_attrs():
            if attr in model_dict:
                if do_copy:
                    if attr in self.namespaces and hasattr(self,attr): # element by element
                        namespace = getattr(self,attr)
                        for k,v in model_dict[attr].__dict__.items():
                            namespace.__dict__[k] = deepcopy(v)
                    else: # full copy
                        setattr(self,attr,deepcopy(model_dict[attr]))
                else:
                    setattr(self,attr,model_dict[attr])

        if model_dict['link_to_cpp']: 
            self.link_to_cpp(force_compile=False)
        else:
            self.cpp = SimpleNamespace()            

    def save(self,drop=[]):
        """ save the model """

        # a. ensure path        
        if not os.path.exists(self.savefolder):
            os.makedirs(self.savefolder)

        # b. create model dict
        model_dict = self.as_dict(drop=drop)

        # b. save to disc
        with open(f'{self.savefolder}/{self.name}.p', 'wb') as f:
            pickle.dump(model_dict, f)

    def load(self,skip=None):
        """ load the model """

        # a. load
        with open(f'{self.savefolder}/{self.name}.p', 'rb') as f:
            model_dict = pickle.load(f)

        self.cpp = SimpleNamespace()
        
        # b. skip selected attributes
        if not skip is None:
            for attr in skip:
                del model_dict[attr]
                
        # c. construct                
        self.from_dict(model_dict)

    def copy(self,name=None,**kwargs):
        """ copy the model """
        
        # a. name
        if name is None: name = f'{self.name}_copy'
        
        # b. model dict
        model_dict = self.as_dict()

        # c. initialize
        other = self.__class__(name=name)

        # d. fill
        other.from_dict(model_dict,do_copy=True)
        other.__update(kwargs)
        
        if hasattr(self,'_ns_specs'): other._ns_specs = self._ns_specs

        if not type(self.cpp) is SimpleNamespace:
            other.link_to_cpp(force_compile=False)
        else:
            other.cpp = SimpleNamespace()

        return other

    ##########
    ## print #
    ##########

    def __str__(self):
        """ called when model is printed """ 
        
        def print_items(sn):
            """ print items in SimpleNamespace """

            description = ''
            nbytes = 0

            for key,val in sn.__dict__.items():

                if np.isscalar(val) and not type(val) is np.bool:
                    description += f' {key} = {val} [{type(val).__name__}]\n'
                elif type(val) is np.bool:
                    if val:
                        description += f' {key} = True\n'
                    else:
                        description += f' {key} = False\n'
                elif type(val) is np.ndarray:
                    description += f' {key} = ndarray with shape = {val.shape} [dtype: {val.dtype}]\n'            
                    nbytes += val.nbytes
                else:                
                    description += f' {key} = ?\n'

            description += f' memory, gb: {nbytes/(10**9):.1f}\n' 
            return description

        description = f'Modelclass: {self.__class__.__name__}\n'
        description += f'Name: {self.name}\n\n'

        description += 'namespaces: ' + str(self.namespaces) + '\n'
        description += 'other_attrs: ' + str(self.other_attrs) + '\n'
        description += 'savefolder: ' + str(self.savefolder) + '\n'
        description += 'cpp_filename: ' + str(self.cpp_filename) + '\n'

        for ns in self.namespaces:
            description += '\n'
            description += f'{ns}:\n'
            description += print_items(getattr(self,ns))

        return description 

    #######################
    ## interact with cpp ##
    #######################

    def link_to_cpp(self,force_compile=True,use_log=True,do_print=False):
        """ link to C++ file """

        self.check_types()
        
        # a. unpack
        filename = self.cpp_filename
        options = self.cpp_options
        
        def structname(ns):

            if ns in self.cpp_structsmap:
                return self.cpp_structsmap[ns]
            else:
                return f'{ns}_struct'
              
        structsmap = {structname(ns):getattr(self,ns) for ns in self.namespaces}

        # b. link to C++
        self.cpp = link_to_cpp(filename,force_compile=force_compile,options=options,
            structsmap=structsmap,use_log=use_log,do_print=do_print)

    ############
    # clean-up #
    ############

    def __del__(self):

        if hasattr(self,'cpp') and (not type(self.cpp) is SimpleNamespace):
            self.cpp.delink()            