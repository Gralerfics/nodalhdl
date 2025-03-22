def static(*args, **kwargs):
    def decorator(func):
        for k, v in {**kwargs, **{k: None for k in args}}.items():
            setattr(func, k, v)
        
        return func
    
    return decorator

