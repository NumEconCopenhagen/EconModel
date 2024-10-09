# -*- coding: utf-8 -*-
""" jit

Functions for call Numba jitted functions.

"""

import traceback

class jit(): 

    def __init__(self,model,show_exc=True): 
        """ load namespace references """

        self.model = model
        self.show_exc = show_exc
        for ns in model.namespaces:
            setattr(self,ns,getattr(model,ns))
      
    def __enter__(self): 
        """ swap from normal namespaces to updated jitted namespaces """ 

        model = self.model
        if model.jit:
            model.update_jit()
            for ns in model.namespaces:
                jit = model._ns_jit[ns]
                setattr(model,ns,jit)

        return model
  
    def __exit__(self, exc_type, exc_value, tb):
        """ swap back to normal namespaces and delete jitted namespaces """

        if exc_type is not None and self.show_exc:
            traceback.print_exception(exc_type, exc_value, tb)
        
        model = self.model
        if model.jit:

            for ns in model.namespaces:
                normal = getattr(self,ns)
                setattr(model,ns,normal)
            
            del model._ns_jit

        if exc_type is None:
            return True
        else:
            return False