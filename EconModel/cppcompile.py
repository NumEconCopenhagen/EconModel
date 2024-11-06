# -*- coding: utf-8 -*-
""" cppcompile

Functions for compiling C++ files to use in Python.

"""

import os
import shutil
import time
import zipfile
import urllib.request
from subprocess import PIPE, run

############
# auxilary #
############

def find_vs_path():
    """ find path to visual studio """

    paths = [   
        'C:/Program Files/Microsoft Visual Studio/2019/Community/VC/Auxiliary/Build/',
        'C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/'
    ]

    for path in paths: 
        if os.path.isdir(path): return path

    raise RuntimeError('no Visual Studio installation found')

def write_setup_omp():
    """ write C++ file to setup OpenMP with Visual Studio """

    assert not os.path.isfile('setup_omp.cpp'), f'setup_omp.cpp already exists'

    with open(f'setup_omp.cpp', 'w') as cppfile:
        
        cppfile.write('#include <windows.h>\n') 
        cppfile.write('#define EXPORT extern "C" __declspec(dllexport)\n')
        cppfile.write('EXPORT void setup_omp(){\n')
        cppfile.write('SetEnvironmentVariable("OMP_WAIT_POLICY", "passive");\n')
        cppfile.write('}\n')

def setup_nlopt(vs_path=None,download=True,unzip=False,folder='cppfuncs/',do_print=False):
    """download and setup nlopt

    Args:

        vs_path (str,optional): path to vs compiler
        download (bool,optional): download nlopt 2.4.2
        unzip (bool,optional): unzip even if not downloaded
        folder (str,optional): folder to put nlopt to
        do_print (bool,optional): print progress

    """

    vs_path = vs_path if not vs_path is None else find_vs_path()

    nloptfolder = f'{folder}nlopt-2.4.2-dll64/'
    if os.path.isdir(nloptfolder):
        if do_print: print('NLopt already installed')
        return

    # a. download
    zipfilename = os.path.abspath(f'{os.getcwd()}/{folder}nlopt-2.4.2-dll64.zip')
    if download:
        url = 'http://ab-initio.mit.edu/nlopt/nlopt-2.4.2-dll64.zip'
        urllib.request.urlretrieve(url,zipfilename)

    # b. unzip
    if download or unzip:
        with zipfile.ZipFile(zipfilename) as file:
            file.extractall(f'{os.getcwd()}/{folder}nlopt-2.4.2-dll64/')

    # c. setup string
    pwd_str = f'cd /d "{os.getcwd()}/{folder}nlopt-2.4.2-dll64/"\n'    
    path_str = f'cd /d "{vs_path}"\n'
    version_str = 'call vcvarsall.bat x64\n'
    setup_str = 'lib /def:libnlopt-0.def /machine:x64'
    
    lines = [path_str,version_str,pwd_str,setup_str]

    if do_print: 
        print('compile.bat:')
        for line in lines: print(line,end='')

    # d. write .bat
    with open('compile_nlopt.bat', 'w') as txtfile:
        txtfile.writelines(lines)

    # e. call .bat
    result = run('compile_nlopt.bat',stdout=PIPE,stderr=PIPE,universal_newlines=True,shell=True)
    if result.returncode == 0:
        if do_print: 
            print('terminal:')
            print(result.stdout)
            print('C++ files compiled')
        if do_print: print('NLopt successfully installed')
    else:
        print('terminal:')
        print(result.stdout)
        raise RuntimeError('NLopt installation failed')

    os.remove('compile_nlopt.bat')

def setup_tasmanian(download=True,unzip=False,folder='cppfuncs/',do_print=False):
    """download and setup Tasmanian 7.0

    Args:

        download (bool,optional): download Tasmanian 7.0
        unzip (bool,optional): unzip even if not downloaded
        folder (str,optional): folder to put Tasmanian to
        do_print (bool,optional): print progress

    """

    tasmanianfolder = f'{os.getcwd()}/{folder}TASMANIAN-7.0/'
    if os.path.isdir(tasmanianfolder):
        if do_print: print('TASMANIAN already installed')
        return

    # a. download
    zipfilename = os.path.abspath(f'{os.getcwd()}/{folder}TASMANIAN-7.0.zip') 
    if download:
        url = 'https://github.com/JeppeDruedahl/TASMANIAN/raw/main/TASMANIAN-7.0.zip'
        urllib.request.urlretrieve(url,zipfilename)
        
    # b. unzip
    if download or unzip:
        with zipfile.ZipFile(zipfilename) as file:
            file.extractall(f'{os.getcwd()}/{folder}')       

    if do_print: print('TASMANIAN successfully installed') 

def setup_alglib(download=True,unzip=False,folder='cppfuncs/',do_print=False):
    """download and setup ALGLIB 3.17

    Args:

        download (bool,optional): download ALGLIB 3.17
        unzip (bool,optional): unzip even if not downloaded
        folder (str,optional): folder to put ALGLIB to
        do_print (bool,optional): print progress

    """

    if os.path.isdir(f'{os.getcwd()}/{folder}alglib-3.17.0'):
        if do_print: print('alglib already installed')
        return

    # a. download
    zipfilename = os.path.abspath(f'{os.getcwd()}/{folder}alglib-3.17.0.cpp.gpl.zip')
    if download:
        url = 'https://www.alglib.net/translator/re/alglib-3.17.0.cpp.gpl.zip'
        urllib.request.urlretrieve(url,zipfilename)
        
    # b. unzip
    if download or unzip:
        with zipfile.ZipFile(zipfilename) as file:
            file.extractall(f'{os.getcwd()}/{folder}alglib-3.17.0')

    if do_print: print('alglib succesfully installed')

def setup_autodiff(download=True,unzip=False,folder='cppfuncs/',do_print=False):
    """download and setup autodiff

    Args:

        download (bool,optional): download autodiff
        unzip (bool,optional): unzip even if not downloaded
        folder (str,optional): folder to put autodiff to
        do_print (bool,optional): print progress

    """

    if os.path.isdir(f'{os.getcwd()}/{folder}autodiff'):
        if do_print: print('autodiff already installed')
        return

    # a. download
    zipfilename = os.path.abspath(f'{os.getcwd()}/{folder}autodiff-main.zip')
    if download:
        url = 'https://github.com/autodiff/autodiff/archive/refs/heads/main.zip'
        urllib.request.urlretrieve(url,zipfilename)
        
    # b. unzip
    if download or unzip:
        with zipfile.ZipFile(zipfilename) as file:
            file.extractall(f'{os.getcwd()}/{folder}')
        
    # c. move
    src = f'{os.getcwd()}/{folder}/autodiff-main/autodiff'
    dst = f'{os.getcwd()}/{folder}/autodiff'
    shutil.move(src,dst)

    # d. clean
    time.sleep(5)
    shutil.rmtree(f'{os.getcwd()}/{folder}/autodiff-main/')

    if do_print: print('autodiff succesfully installed')

def setup_Eigen(download=True,unzip=False,folder='cppfuncs/',do_print=False):
    """download and setup autodiff

    Args:

        download (bool,optional): download Eigen 3.4.0
        unzip (bool,optional): unzip even if not downloaded
        folder (str,optional): folder to put Eigen to
        do_print (bool,optional): print progress

    """

    if os.path.isdir(f'{os.getcwd()}/{folder}Eigen'):
        if do_print: print('Eigen already installed')
        return

    # a. download
    zipfilename = os.path.abspath(f'{os.getcwd()}/{folder}Eigen-main.zip')
    if download:
        url = 'https://gitlab.com/libeigen/eigen/-/archive/3.4.0/eigen-3.4.0.zip'
        urllib.request.urlretrieve(url,zipfilename)
        
    # b. unzip
    if download or unzip:
        with zipfile.ZipFile(zipfilename) as file:
            file.extractall(f'{os.getcwd()}/{folder}')
        
    # c. move
    src = f'{os.getcwd()}/{folder}/eigen-3.4.0/Eigen'
    dst = f'{os.getcwd()}/{folder}/Eigen'
    shutil.move(src,dst)

    # d. clean
    time.sleep(2)
    shutil.rmtree(f'{os.getcwd()}/{folder}/eigen-3.4.0')

    if do_print: print('Eigen succesfully installed')

def add_macros(macros):
    """ add macros to compile string
        
    Args:

        macros (dict/list): preprocessor macros

    Returns:

        compile_str (str): macro string 

    """

    compile_str = ''

    if type(macros) is dict:
    
        for k,v in macros.items():
            if v is None:
                compile_str += f' /D{k}'
            else:
                compile_str += f' /D{k}={v}'
    
    elif type(macros) is list:

        for k in macros: 
            compile_str += f' /D{k}'

    return compile_str

###########
# compile #
###########

def set_default_options(options):
    """

    Args:

        options (dict): compiler options with 

            compiler (str): compiler choice (vs or intel)
            vs_path (str): path to vs compiler 
                (if None then newest version found is used, 
                e.g. C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Auxiliary/Build/)
            intel_path (str): path to intel compiler
            flags (list[str]): list of flags (default is None)
                vs if None: /LD /EHsc /O2 /openmp
                intel if None: /LD /EHsc /O3 /openmp
            nlopt_lib (str): path to NLopt library 
                (included if exists, default is cppfuncs/nlopt-2.4.2-dll64/libnlopt-0.lib)
            tasmanian_lib (str): path to Tasmanian library 
                (included if exists, default is cppfuncs/TASMANIAN-7.0/lib/tasmaniansparsegrid.lib')
            additional_cpp (str): additional cpp files to include ('' default)
            dllfilename (str): filename of resulting dll file (if None (default) based on .cpp file)
            macros (dict/list): preprocessor macros

    """

    options.setdefault('compiler','vs')
    
    if options['compiler'] == 'vs':
        options.setdefault('vs_path',find_vs_path())
    else:
        options.setdefault('vs_path',None)

    options.setdefault('intel_path','C:/Program Files (x86)/Intel/oneAPI')

    options.setdefault('flags',None)
    options.setdefault('nlopt_lib','cppfuncs/nlopt-2.4.2-dll64/libnlopt-0.lib')
    options.setdefault('tasmanian_lib','cppfuncs/TASMANIAN-7.0/lib/tasmaniansparsegrid.lib')
    options.setdefault('additional_cpp','')
    options.setdefault('macros',None)
    options.setdefault('dllfilename',None)

    assert options['compiler'] in ['vs','intel'], f'unknown compiler {options["compiler"]}'

def compile(filename,options=None,do_print=False):      
    """compile cpp file to dll

    Args:

        filename (str): path to .cpp file
        options (dict,optional): compiler options
        do_print (bool,optional): print if succesfull

    """
    
    if options is None: options = {}
    set_default_options(options)

    if options['compiler'] == 'vs' and options['vs_path'] is None:
        options['vs_path'] = find_vs_path()

    compiler = options['compiler']
    vs_path = options['vs_path']
    intel_path = options['intel_path']
    flags = options['flags']
    nlopt_lib = options['nlopt_lib']
    tasmanian_lib = options['tasmanian_lib']
    additional_cpp = options['additional_cpp']
    macros = options['macros']
    dllfilename = options['dllfilename']
    
    # a. check filename
    assert os.path.isfile(filename), f'"{filename}" does not exist'

    basename = os.path.basename(filename)
    _dirname = os.path.dirname(filename)

    # b. prepare visual studio
    if compiler == 'vs':
        write_setup_omp()

    # c. check for libraries
    nlopt_lib = f' {nlopt_lib} ' if os.path.isfile(nlopt_lib) else ''
    tasmanian_lib = f' {tasmanian_lib} ' if os.path.isfile(tasmanian_lib) else ''
    setup_omp = ' setup_omp.cpp' if compiler == 'vs' else ''
    libs = f'{setup_omp}{nlopt_lib}{tasmanian_lib}{additional_cpp}'[1:]

    # d. compile string
    pwd_str = 'cd /d "' + os.getcwd() + '"\n'    
    
    if compiler == 'vs':
        
        path_str = f'cd /d "{vs_path}"\n'
        version_str = 'call vcvarsall.bat x64\n'
        
        compile_str = f'cl'
        flags = '/LD /EHsc /O2 /openmp' if flags is None else flags
        compile_str += f' {flags} {filename} {libs} {add_macros(macros)}\n' 

        lines = [path_str,version_str,pwd_str,compile_str]

    elif compiler == 'intel':
        
        path_str = f'cd /d "{intel_path}"\n'
        version_str = f'call setvars.bat\n'
        
        compile_str = f'icx'
        flags = '/LD /EHsc /O3 /openmp' if flags is None else flags
        compile_str += f' {flags} {filename} {libs} {add_macros(macros)}\n' 

    lines = [path_str,version_str,pwd_str,compile_str]
        
    if do_print: 
        print('compile.bat:')
        for line in lines: print(line,end='')
        print('')

    # e. write .bat
    with open('compile.bat', 'w') as txtfile:
        txtfile.writelines(lines)
                               
    # f. compile
    result = run('compile.bat',stdout=PIPE,stderr=PIPE,universal_newlines=True,shell=True)

    if compiler == 'vs': 
        os.remove(f'setup_omp.cpp')
        os.remove(f'setup_omp.obj')

    if result.returncode == 0:
        if do_print: 
            print('terminal:')
            print(result.stdout)
            print(result.stderr)
            print('C++ files compiled')
    else: 
        print('terminal:')
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError('C++ files can not be compiled')

    # g. rename dll
    filename_raw = os.path.splitext(basename)[0]
    if dllfilename is None: 
        dllfilename = f'{filename_raw}.dll'  
    else:
        os.replace(f'{filename_raw}.dll',dllfilename)

    # h. clean up
    os.remove('compile.bat')
    if compiler == 'vs':
        os.remove(f'{filename_raw}.obj')
        os.remove(f'{filename_raw}.lib')
        os.remove(f'{filename_raw}.exp')    
    elif compiler == 'intel':
        os.remove(f'{filename_raw}.lib')
        os.remove(f'{filename_raw}.exp')