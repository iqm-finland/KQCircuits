try:
    import pya
except ImportError:
    import klayout.db as pya


def is_standalone_session():        
    try:
        app = pya.Application
    except AttributeError:
        standalone = True
    else:
        standalone = False
    
    return standalone
    
