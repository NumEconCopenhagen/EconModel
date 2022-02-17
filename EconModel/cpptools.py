# -*- coding: utf-8 -*-
""" cpptools

Functions for calling C++ files from Python.

"""

import os
import ctypes as ct
import re
import numpy as np

from.cppcompile import setup_nlopt, setup_tasmanian, setup_alglib, setup_autodiff, setup_Eigen

from .cppcompile import compile, set_default_options
from .cppstruct import setup_struct, get_struct_pointer

#################
# file analysis #
#################

def find_all_filenames(filename,do_print=False):
    """ find all included MYFILES on the form '#include "MYFILE.cpp"' in filename 
    
    Note: Deeper nested includes not included.

    Args:

        filename (str): filename to search in
        do_print (bool,optional): print progress

    Returns:

        all_filenames (list): list of filenames

    """

    first = True
    if do_print: print(f'\n### finding all included files ###\n')

    dirname = os.path.dirname(filename)
    all_filenames = [filename]

    # a. retrieve code
    with open(filename, 'r') as file: code = file.read()

    # b. find includes
    include_strs = re.findall(r'#include\s*"\s*.*?.cpp\s*"',code)
    for include_str in include_strs:
        
        include = include_str
        include = include.replace('#include','')
        include = include.replace('\n','')
        include = include.replace('"','')
        include = include.replace(' ','')
        
        if do_print: print(include)

        all_filenames.append(f'{dirname}/{include}')

    return all_filenames

def analyze_cpp(funcs,filename,structnames=[],do_print=False):
    """ analyse cpp-file in filename and add functions to funcs

        funcs (dict): with funcnames as keys and (argtypes,restype) as values 
        filename (str): filename to analyze
        structnames (list,optional): list of structs used
        do_print (bool,optional): print progress

    """

    if do_print: print(f'### analyzing {filename} ###\n')

    # a. allowed types
    all_restypes = ['void','double','int','bool','void*']
    all_argtypes = ['double*','double','int*','int','bool*','bool','char*','char','void*'] 
    all_argtypes += [f'{structname}*' for structname in structnames]

    # b. retrieve code
    with open(filename, 'r') as file: code = file.read()
        
    # c. rough cleaning
    code = code.replace('\n','')
    code = code.replace('#define EXPORT extern "C" __declspec(dllexport)','')
    code = re.sub(r'\/\*.*?\*\/',' ',code)

    # d. loop through all functions
    func_strs = re.findall(r'EXPORT.*?\(.*?\)',code)
    for func_str in func_strs:

        # i. return type
        restype = re.search(r'EXPORT\s+.*?\s+',func_str).group(0).replace('EXPORT','').replace(' ','')

        # ii. function name
        if restype == 'void*': 
            restype_ = r'void\*'
        else:
            restype_ = restype 
        funcname = re.search(fr'{restype_} .*?\(',func_str).group(0).replace(restype,'').replace('(','').replace(' ','')
        
        # iii. argument types
        argtypes = []
        if re.search(r'\(\s*\)', func_str) is None:

            argtypes_raw = re.search(r'\(.*?\)',func_str).group(0).replace('(','').replace(')','').split(',')
            for argtype_raw in argtypes_raw:
                
                # o. pointer
                pointer = '*' if '*' in argtype_raw else ''
                Npointer = argtype_raw.count('*')
                
                # oo. type
                argtype_no_pointer = argtype_raw.replace('*','')
                argtype = re.search(r'\s*.*?\s+',argtype_no_pointer).group(0).replace(' ','')

                argtypes.append(argtype + pointer*Npointer)

        # iv. chekcs
        return_check = (restype in all_restypes)
        arg_check = all([ (argtype in all_argtypes or argtype is None) for argtype in argtypes])

        if (not return_check) or (not arg_check) or do_print:

            print(f'function: {funcname}')
            print(f'return type: {restype}')
            print(f'argument types: {argtypes}')

        assert return_check, 'return type not allowed, should by in ' + str(all_restypes) 
        assert arg_check, 'not all argument types not allowed, should by in ' + str(all_argtypes) 
        
        # v. update
        funcs[funcname] = (argtypes,restype)
        if do_print: print('')
     
##########    
# linker #
##########

class link_to_cpp():

    def __init__(self,filename,force_compile=True,structsmap={},
                      options={},use_log=True,print_log=True,do_print=False):
        """ link to C++ file

        Args:

            filename (str): C++ file with .cpp extension (full path)
            force_compile (bool,optional): compile even if .dll is present
            structsmap (dict,optional): struct names as keys and associated pythonobj used in C++ as values
            options (dict,optional): compiler options
            use_log (bool,optional): assumes log is printed to filename.log (deleted afterwards, saved in self.log[funcname])
            print_log (bool,optional): print log to screen when function is called
            do_print (bool,optional): print progress

        """

        assert os.path.isfile(filename), f'"{filename}" does not exist'
        if do_print: print(f'Linking to: {filename}')

        # a. file structure
        self.filename = filename
        self.basename = os.path.basename(self.filename)        
        self.dirname = os.path.dirname(self.filename)
        self.filename_raw = os.path.splitext(self.basename)[0]

        # b. options
        self.structsmap = structsmap 
        self.options = options
        self.use_log = use_log
        self.print_log = print_log
        self.log = {}
        
        self.compile(force_compile=force_compile,do_print=do_print)

    ###########
    # compile #
    ###########

    def compile(self,force_compile=True,do_print=False):
        """ compile and link to C++ file

        Args:

            force_compile (bool,optional): compile even if .dll is present
            do_print (bool,optional): print progress

        """

        # a. find all filenames
        self.all_filenames = find_all_filenames(self.filename,do_print=do_print)

        # b. setup all structs
        self.structs = {}
        self.structfiles = {}
        if do_print: print('\n### writing structs ###\n')
        
        for structname,struct in self.structsmap.items():

            self.structfiles[structname] = f'{self.dirname}/{structname}.cpp'
            if do_print: print(self.structfiles[structname])
            
            self.structs[structname] = setup_struct(struct,structname,self.structfiles[structname],do_print=do_print)
            
        # c. analyze functions
        structnames = [key for key in self.structs.keys()]

        self.funcs = {}
        for filename in self.all_filenames: 
            analyze_cpp(self.funcs,filename,structnames,do_print=do_print)

        # d. compile
        if do_print: print('### compiling and linking ###\n')

        if 'dllfilename' in self.options and (not self.options['dllfilename'] is None):
            self.dllfilename = f'{os.getcwd()}\{self.options["dllfilename"]}'
        else:
            self.dllfilename = f'{os.getcwd()}\{self.filename_raw}.dll'

        if not 'nlopt_lib' in self.options:
            self.options['nlopt_lib'] = f'{self.dirname}/nlopt-2.4.2-dll64/libnlopt-0.lib'
        
        if not 'tasmanian_lib' in self.options:
            self.options['tasmanian_lib'] = f'{self.dirname}/TASMANIAN-7.0/lib/tasmaniansparsegrid.lib'

        if not os.path.isfile(self.dllfilename) or force_compile:
            compile(self.filename,options=self.options,do_print=do_print)
        else:
            set_default_options(self.options)

        # e. link

        # NLopt and tasmanian hacks - begin
        do_nlopt = os.path.isfile(self.options['nlopt_lib'])
        do_tasmanian = os.path.isfile(self.options['tasmanian_lib'])
        if do_nlopt: nloptfile = ct.cdll.LoadLibrary(f'{self.dirname}/nlopt-2.4.2-dll64/libnlopt-0.dll')
        if do_tasmanian: tasmanianfile = ct.cdll.LoadLibrary(f'{self.dirname}/TASMANIAN-7.0/bin/tasmaniansparsegrid.dll')

        # load
        self.cppfile = ct.cdll.LoadLibrary(self.dllfilename)

        # hack for OpenMP in Visual Studio
        if self.options['compiler'] == 'vs':

            self.cppfile.setup_omp()
            self.delink()
            self.cppfile = ct.cdll.LoadLibrary(self.dllfilename)
        
        # NLopt and tasmanian hacks - end
        if do_nlopt: self.delink(cppfile=nloptfile,do_print=False)
        if do_tasmanian: self.delink(cppfile=tasmanianfile,do_print=False)

        # set types
        self.__set_types()
        if do_print: print('C++ files loaded\n')

        # f. function call method
        def __call_func(name): return lambda *x: self.__call_func(name,*x)
        for funcname in self.funcs.keys():
            setattr(self,funcname,__call_func(funcname))

        if do_print: print('DONE!\n')

    def __set_types(self):
        """ set types for return and arguments for all functions """

        for funcname,(argtypes_raw,restype_raw) in self.funcs.items():
                
            # a. arguments
            argtypes = []
            for argtype_raw in argtypes_raw:

                if (argtype_raw_struct := argtype_raw.replace('*','')) in self.structs:
                    argtype = ct.POINTER(self.structs[argtype_raw_struct])
                elif argtype_raw == 'int*':
                    argtype = ct.POINTER(ct.c_long)
                elif argtype_raw == 'double*':
                    argtype = ct.POINTER(ct.c_double)
                elif argtype_raw == 'int':
                    argtype = ct.c_long
                elif argtype_raw == 'double':
                    argtype = ct.c_double
                elif argtype_raw == 'bool':
                    argtype = ct.c_bool
                elif argtype_raw == 'char*':
                    argtype = ct.c_char_p
                elif argtype_raw == 'void*':
                    argtype = ct.c_void_p                                 
                else:
                    raise Exception(f'argument type {argtype_raw} not allowed')
                
                argtypes.append(argtype)

            # b. return
            if restype_raw == 'void':
                restype = None
            elif restype_raw == 'int':
                restype = ct.c_long
            elif restype_raw == 'double':
                restype = ct.c_double
            elif restype_raw == 'bool':
                restype = ct.c_bool
            elif restype_raw == 'void*':
                restype = ct.c_void_p                
            else:
                raise Exception(f'return type {restype_raw} not allowed')

            # c. set
            funcnow = getattr(self.cppfile,funcname)
            funcnow.restype = restype
            if len(argtypes) > 0:
                funcnow.argtypes = argtypes
                    
    def delink(self,cppfile=None,do_print=False):
        """ delink C++ library 

        Args:

            cppfile (cdll,optional): loaded .dll file to delink
            do_print (bool,optional): print progess

        """

        if cppfile is None: cppfile = self.cppfile

        # a. get handle
        handle = cppfile._handle
    
        # b. delete linking variable
        del cppfile

        # c. free handle
        ct.windll.kernel32.FreeLibrary.argtypes = [ct.wintypes.HMODULE]
        ct.windll.kernel32.FreeLibrary(handle)
        
        if do_print: print('C++ files delinked')

    def recompile(self,force_compile=True,use_log=True,print_log=True,do_print=False):
        """ re-compile and link to C++ file

        Args:

            force_compile (bool,optional): compile even if .dll present
            do_print (bool,optional): print progress

        """

        self.use_log = use_log
        self.print_log = print_log

        self.delink()
        self.compile(force_compile=force_compile,do_print=do_print)

    #####################
    # calling functions #
    #####################
    
    def __get_p_args(self,funcname,args):
        """ get pointers to arguments """

        p_args = []

        argtypes_raw,_restype_raw = self.funcs[funcname]
        for arg,argtype_raw in zip(args,argtypes_raw):

            if (argtype_raw_struct := argtype_raw.replace('*','')) in self.structs:
                p_arg = get_struct_pointer(arg,self.structs[argtype_raw_struct])
            elif argtype_raw in ['int*','double*','bool*']:
                p_arg = np.ctypeslib.as_ctypes(arg.ravel())
            elif argtype_raw in ['double','int','bool']:
                p_arg = arg
            elif argtype_raw == 'char*':
                p_arg = arg.encode()
            elif argtype_raw == 'void*':
                p_arg = arg                
            else:
                raise Exception(f'unknown argument {argtype_raw} with type {argtype_raw}')

            p_args.append(p_arg)

        return p_args

    def __call_func(self,funcname,*args):
        """ call function 
        
        Args:

            funcname (str): function to call
            *args: arguments to function

        Returns

            (None/int/double/bool): return of function

        """
        
        for n in range(2):

            try:

                p_args = self.__get_p_args(funcname,args)
                funcnow = getattr(self.cppfile,funcname)
                result = funcnow(*p_args)
                break

            except Exception as e:

                if n == 0: self.compile(force_compile=False) # re-linking might solve the problem
                if n == 1: print(e) # print error message

        # print log
        if self.use_log:

            log_filename = f'{self.filename_raw}.log'
            if os.path.isfile(log_filename):

                self.log[funcname] = ''
                with open(log_filename,'r') as file:
                    for line in file.readlines():
                        if self.print_log: print(line,end='')
                        self.log[funcname] += line
            
                os.remove(log_filename)

        # return
        return result


    ############
    # clean up #
    ############

    def clean_up(self):
        """ remove dll filename and structs """

        if hasattr(self,'cppfile'): self.delink()
        os.remove(self.dllfilename)
        for structname in self.structfiles.values():
            os.remove(structname)

    def __del__(self):

        if hasattr(self,'cppfile'): self.delink()            