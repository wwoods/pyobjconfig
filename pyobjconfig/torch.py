from .common import ConfigurableObject

import torch

class ConfigurableModule(ConfigurableObject, torch.nn.Module):
    """Pytorch overrides __setattr__ in a way that is incompatible with
    ConfigurableObject.  This class works around that.
    """

    def __init__(self, *args, **kwargs):
        torch.nn.Module.__init__(self)
        ConfigurableObject.__init__(self, *args, **kwargs)

    def __setattr__(self, name, value):
        torch.nn.Module.__setattr__(self, name, value)
        object.__setattr__(self, name, value)


    def state_restore(self, d):
        """Used to restore state previously saved via Pickle.
        """
        pass


    def state_to_save(self):
        """Pytorch's state_dict may not always be appropriate.  In that case,
        use state_to_save() and state_restore().
        """
        return {}

