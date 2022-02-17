# EconModel

A small code library for easily working with economic models in Python with three objectives:

1. Provide standard functionality for copying, saving and loading.
1. Provide an easy interface to call [numba](http://numba.pydata.org/) JIT compilled functions.
1. Provide an easy interface to call C++ functions.

Examples are shown in [EconModelNotebooks](https://github.com/NumEconCopenhagen/EconModelNotebooks).

# Installation

The package can be installed with

```
pip install EconModel
```

# Usage

**Basic usage** starts with:

```
from EcnoModel import EconModelClass
class MyModelClass(EconModelClass):
    
    def settings(self):
        pass

    def setup(self):
        pass

    def allocate(self):
        pass        

mymodel = MyModelClass(name='mymodel')
```

The model is **required** to have the following three methods:

1. `.settings()`: Choose fundamental settings.
1. `.setup()`: Set free parameters.
1. `.allocate()`: Set compound parameters and allocate arrays.

When the model is initialized `.settings`, `.setup` and `.allocate` are all called (in that order). Afterwards all namespace elements should not change type, and arrays should not change number of dimensions, though they can change shape.

In `.settings()` the following internal attributes can be specified:

1. `self.savefolder = str`: Filepath to save in and load from (default: saved).
1. `self.namespaces = [str]`: List of namespaces available in numba and C++ functions.
1. `self.other_attrs = [str]`: List of additional attributes to be copied and saved.
1. `self.cpp_filename = str`: Filepath of C++ file to link to.

 The namespaces `.par`, `.sim`, and `.sol` are always available.

 The following **standard functionality** is provided:

1. `.copy()`: Copy model.
1. `.save()`: Saves model in `savefolder/name`.
1. `.as_dict()`: Returns model packaged in a dictionary.
1. `.link_to_cpp()`: Compile and link to C++ file.

A saved model can be **loaded** as:

```
mymodel = MyModelClass(name='mymodel',load=True,skipattrs=None)
```

Where `skipattrs [str]`  is a list of attributes to *not* load.

A model can be **created from a dictionary** as:

```
mymodeldict = mymodel.as_dict()
mymodel_new = MyMOdelClass(name='mymodel',from_dict=mymodeldict)
```

A **numba function** is called as e.g.:

```
from EcnoModel import jit
with jit(mymodel) as mymodel_jit:
    numba_function(mymodel_jit.par)
```

**C++ functions** are called as e.g.:

```
mymodel.cpp.cpp_funct(mymodel.par)
```

The libarary also contains interfaces to C++ packages such as:

1. [NLopt 2.4.2](https://nlopt.readthedocs.io/en/latest/)
1. [TASMANIAN 7.0](https://github.com/ORNL/TASMANIAN/)
1. [ALGLIB 3.17](https://www.alglib.net/)
1. [Eigen](https://eigen.tuxfamily.org/index.php?title=Main_Page)
1. [autodiff](https://autodiff.github.io/)

# Development

To develop the package follow these steps:

1. Clone this repository
2. Locate the cloned repostiory in a terminal
4. Run `pip install -e .`

Changes you make to the package is now immediately effective on your own computer. 
