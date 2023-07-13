# -*- coding: utf-8 -*-
""" cppstruct

Functions for using dict-like objects in Python in C++.

"""

import ctypes as ct
import numpy as np

def get_fields(pythonobj,structname):
    """ construct ctypes list of fields from pythonobj
    
    Args:
    
        pythonobj: e.g. class, SimpleNamespace or namedtuple
        structname (str): name of C++ struct

    Returns:
    
        ctlist (list): list of fields with elements (name,ctypes type) 
        cttxt (str): string with content of C++ struct
        ctfuncttxt (str): dictionary with content of get_ functions to C++ struct

    """

    ctlist = []
    cttxt = ''
    ctfunctxt = {}

    # a. update function for ctfunctxt
    def ctfunctxt_update(typename,key):
        
        if not typename in ctfunctxt:

            typename_p = typename.replace('*','_p')
            ctfunctxt[typename] = f'{typename} get_{typename_p}_{structname}'
            ctfunctxt[typename] += f'({structname}* x, char* name){{\n\n'

        ctfunctxt[typename] += f' if( strcmp(name,"{key}") == 0 ){{ return x->{key}; }}\n else'

    # b. main
    for key,val in pythonobj.__dict__.items():

        # i. scalars
        if np.isscalar(val):

            if type(val) in [int,np.int_]:
        
                ctlist.append((key,ct.c_long))
                cttxt += f' int {key};\n'
                ctfunctxt_update('int',key)
        
            elif type(val) in [float,np.float_]:
            
                ctlist.append((key,ct.c_double))          
                cttxt += f' double {key};\n'
                ctfunctxt_update('double',key)

            elif type(val) in [bool,np.bool_]:
        
                ctlist.append((key,ct.c_bool))
                cttxt += f' bool {key};\n'
                ctfunctxt_update('bool',key)
            
            elif type(val) is str:

                ctlist.append((key,ct.c_char_p))
                cttxt += f' char* {key};\n' 
                ctfunctxt_update('char*',key)

            else:

                raise ValueError(f'unknown scalar type for {key}, type is {type(val)}')
        
        # ii. arrays
        else:

            assert hasattr(val,'dtype'), f'{key} is neither scalar nor np.array'
            
            if val.dtype == np.int_:

                ctlist.append((key,ct.POINTER(ct.c_long)))               
                cttxt += f' int* {key};\n'
                ctfunctxt_update('int*',key)
                     
            elif val.dtype == np.float_:
            
                ctlist.append((key,ct.POINTER(ct.c_double)))
                cttxt += f' double* {key};\n'
                ctfunctxt_update('double*',key)

            elif val.dtype == np.bool_:
            
                ctlist.append((key,ct.POINTER(ct.c_bool)))
                cttxt += f' bool* {key};\n'
                ctfunctxt_update('bool*',key)

            else:
                
                raise ValueError(f'unknown array type for {key}, dtype is {val.dtype}')
    
    # c. finalize ctfunctxt    
    for typename in ctfunctxt.keys():

        if typename == 'int':
            ctfunctxt[typename] += ' {return -9999;}\n\n}\n' # for catching errors
        elif typename == 'double':
            ctfunctxt[typename] += ' {return NAN;}\n\n}\n'
        elif typename == 'bool':
            ctfunctxt[typename] += ' {return false;}\n\n}\n' # cannot catch errors
        elif typename == 'char*':
            ctfunctxt[typename] += ' {return NULL;}\n\n}\n'
        elif typename == 'int*':
            ctfunctxt[typename] += ' {return NULL;}\n\n}\n'
        elif typename == 'double*':
            ctfunctxt[typename] += ' {return NULL;}\n\n}\n'
        elif typename == 'bool*':
            ctfunctxt[typename] += ' {return NULL;}\n\n}\n'

    return ctlist,cttxt,ctfunctxt

def setup_struct(pythonobj,structname,structfile,do_print=False):
    """ create ctypes struct from setup_struct
    
    Args:
    
        pythonobj: e.g. class, SimpleNamespace or namedtuple (with __dict__ method)
        structname (str): name of C++ struct
        strucfile (str): name of of filename for C++ struct
        do_print (bool): print contents of structs

    Write strutfile with C++ struct called structname.

    Returns:

        ctstruct (class): ctypes struct type with elements from pythonobj

     """

    assert hasattr(pythonobj,'__dict__'), f'python object does not have a dictionary interface'
    assert type(structname) is str
    assert type(structfile) is str

    # a. get fields
    ctlist, cttxt, ctfunctxt = get_fields(pythonobj,structname)

    if do_print: print(cttxt)
    
    # b. write cpp file with struct
    with open(structfile, 'w') as cppfile:

        cppfile.write(f'typedef struct {structname}\n') 
        cppfile.write('{\n')
        cppfile.write(cttxt)
        cppfile.write('}')
        cppfile.write(f' {structname};\n\n')
        for typename in ctfunctxt.keys():
            cppfile.write(ctfunctxt[typename])
            cppfile.write(f'\n\n')
        
    # c. ctypes struct
    class ctstruct(ct.Structure):
        _fields_ = ctlist

    return ctstruct

def get_pointers(pythonobj,ctstruct):
    """ construct ctypes struct class with pointers from pythonobj
    
    Args:
    
        pythonobj: e.g. class, SimpleNamespace or namedtuple
        ctstruct (class): ctypes struct type

    Returns:
    
        p_ctstruct (class): ctypes struct with pointers to pythonobj
        
    """

    # a. setup
    p_ctstruct = ctstruct()
    
    # b. add fields
    for field in ctstruct._fields_:
        
        key = field[0]                
        val = getattr(pythonobj,key)
       
        if isinstance(field[1](),ct.c_long):
            try:
                setattr(p_ctstruct,key,val)
            except:
                raise Exception(f'{key} is not an integer')

        elif isinstance(field[1](),ct.POINTER(ct.c_long)):
            assert np.issubdtype(val.dtype, np.int_), f'field = {field}'
            setattr(p_ctstruct,key,np.ctypeslib.as_ctypes(val.ravel()[0:1])) 
            # why [0:1]? hack to avoid bug for arrays with more elements than highest int32

        elif isinstance(field[1](),ct.c_double):
            try:
                setattr(p_ctstruct,key,val)   
            except:
                raise Exception(f'{key} is not a floating point')

        elif isinstance(field[1](),ct.POINTER(ct.c_double)):
            assert np.issubdtype(val.dtype, np.float_), f'field = {field}'
            setattr(p_ctstruct,key,np.ctypeslib.as_ctypes(val.ravel()[0:1]))
            # why [0:1]? hack to avoid bug for arrays with more elements than highest int32
        
        elif isinstance(field[1](),ct.c_bool):
            setattr(p_ctstruct,key,val)

        elif isinstance(field[1](),ct.POINTER(ct.c_bool)):
            assert np.issubdtype(val.dtype, np.bool_), f'field = {field}'
            setattr(p_ctstruct,key,np.ctypeslib.as_ctypes(val.ravel()[0:1]))
            # why [0:1]? hack to avoid bug for arrays with more elements than highest int32            
        
        elif isinstance(field[1](),ct.c_char_p):
            assert type(val) is str, f'field = {field}'
            setattr(p_ctstruct,key,val.encode())

        else:

            raise ValueError(f'no such type, variable {key}')
    
    return p_ctstruct

def get_struct_pointer(pythonobj,ctstruct):
    """ return pointer to ctypes struct
    
    Args:
    
        pythonobj: e.g. class, SimpleNamespace or namedtuple
        ctstruct (class): ctypes struct type

    Returns:
    
        pointer: pointer to ctypes struct with pointers to pythonobj
    
    """

    return ct.byref(get_pointers(pythonobj,ctstruct))