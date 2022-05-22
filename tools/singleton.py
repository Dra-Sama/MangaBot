class LanguageSingleton(type):
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        lang = kwargs.get("language")
        if lang:
            if (cls, lang) not in cls._instances:
                cls._instances[(cls, lang)] = super(LanguageSingleton, cls).__call__(*args, **kwargs)
            return cls._instances[(cls, lang)]
        if cls not in cls._instances:
            cls._instances[cls] = super(LanguageSingleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
