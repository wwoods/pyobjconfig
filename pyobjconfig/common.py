"""Configuration framework, uses ``pydantic`` in combination with ``argparse``.

Very tied to convention that a "-" in a parameter name refers to a property
on a sub-object.

Also supports environment variables, e.g. --model-batch_size can be specified
as ML_MODEL_BATCH_SIZE.  Useful primarily for dataset locations.
"""

import enum
import functools
import os
import pydantic
import re
import sys

missing = {}

def _init_wrapper(fn):
    @functools.wraps(fn)
    def inner(self, *args, **kwargs):
        if 'child_configurables' not in kwargs:
            raise ValueError("Do not create a ConfigurableObject directly; "
                    "instead, use Class.argparse_create(dict)")
        return fn(self, *args, **kwargs)
    return inner


class ConfigurableObject:
    """Leaning heavily on `pydantic`, create a configurable hierarchy of
    objects.

    Note: if using with torch.nn.Module, use model.common.ConfigurableModule
    instead.  This is because `torch.nn.Module` redefines `__setattr__` in a
    way that is incompatible with configuration.

    If used in any multiple-inheritance situation, the `__init__` methods must
    be explicitly called in order (do not use `super().__init__()`).
    """
    config = None
    config_defaults = None
    config_hparams_extra = None

    @_init_wrapper
    def __init__(self, *, config, child_configurables):
        # Overwrite class-based method
        if self.config is not None:
            # Invoke pydantic validation, etc
            extra_keys = set(config.keys()).difference(
                    self.config.schema()['properties'].keys())
            try:
                if extra_keys:
                    raise ValueError(f'Extra keys: {extra_keys}')
                self.config = self.config(**config)
            except:
                raise ValueError(f'During {self.config} init from {config}')
        elif config:
            raise ValueError(f'Extra keys: {config.keys()}')

        self.config_hparams_extra = {}
        for k, v in child_configurables.items():
            if isinstance(v, _ConfigurableChildWithExtraHparams):
                setattr(self, k, v.value)
                self.config_hparams_extra.update(v.hparams)
            elif issubclass(getattr(self, k), ConfigurableObject):
                setattr(self, k, v)
            else:
                raise NotImplementedError(getattr(self, k))

        # DO NOT call super().__init__().  Classes inheriting
        # ConfigurableObject must be smart enough to call its __init__()
        # manually next to any multiply-inherited members.
        # In e.g. model.common.model.ConfigurableModel, calling
        # super().__init__() here results in pytorch forgetting about any
        # child modules.
        #super().__init__()


    @classmethod
    def argparse_create(cls, args, env=None):
        # Copy args and get rid of "unspecified" values.
        args = {k: v for k, v in args.items() if v is not None}
        r = cls._argparse_create(env, '', args)
        assert not args, args
        return r


    @classmethod
    def argparse_setup(cls, parser):
        cls._argparse_setup('', parser)


    def argparse_hparams(self):
        settings = {}
        self._argparse_hparams(self, '', settings)
        def m(v):
            if isinstance(v, enum.Enum):
                return v.value
            return v
        settings = {k: m(v) for k, v in settings.items()}
        return settings


    @classmethod
    def with_defaults(cls, *args, **kwargs):
        default_vals = {}
        if len(args) != 0:
            assert len(args) == 1, 'Args must be a single dict'
            default_vals.update(args[0])
        default_vals.update(kwargs)
        return type(cls.__name__ + 'WithDefaults', (cls,),
                {'config_defaults': default_vals})


    @classmethod
    def _argparse_check_env(cls, env_prefix, prefix, k, args):
        """If {prefix}{k} exists in environment (upper-case), set that value
        on ``args`` if it doesn't already exist.
        """
        if env_prefix is None:
            return

        argname = f'{prefix}{k}'
        name = f'{env_prefix}_{prefix}{k}'.upper().replace('-', '_')
        v = os.environ.get(name)
        if v is not None:
            args.setdefault(argname, v)


    @classmethod
    def _argparse_setup(cls, prefix, parser):
        """Note that help messages grabbed from config class docstring,
        using format :param i: blah.
        """
        if cls.config is not None:
            assert issubclass(cls.config, pydantic.BaseModel)

            docs = cls.config.__doc__
            props = {}
            if docs is not None:
                last_name = None
                last_prop = None
                def finalize():
                    nonlocal last_name, last_prop
                    if last_name is not None:
                        props[last_name] = '\n'.join(last_prop)
                        last_name = None
                        last_prop = None
                for line in docs.split('\n'):
                    m = re.search(r'^[ \t]*:param ([a-zA-Z0-9_]+):', line)
                    if m is None:
                        if not line.strip():
                            finalize()
                        elif last_name is not None:
                            last_prop.append(line)
                    else:
                        finalize()
                        last_name = m.group(1)
                        last_prop = [line[m.end():]]
                finalize()

            for k, v in cls.config.schema()['properties'].items():
                if k.startswith('_'): continue
                name = f'{prefix}{k}'
                help = props.get(k) or ''
                if 'default' in v:
                    help = help + f'  Default: {v["default"]}'
                kw = {}
                if v.get('type') == 'array':
                    kw['action'] = 'append'
                parser.add_argument(f'--{name}', dest=name, help=help, **kw)
        for k in dir(cls):
            v = getattr(cls, k)
            if type(v) is type and issubclass(v, ConfigurableObject):
                v._argparse_setup(prefix + k + '-', parser)


    def _argparse_hparams(self, root, prefix, hparams):
        if self.config is not None:
            for k in self.config.schema()['properties'].keys():
                if k.startswith('_'): continue
                docname = f'{prefix}{k}'
                hparams[docname] = getattr(self.config, k)
        for k, v in self.config_hparams_extra.items():
            if k in hparams:
                raise ValueError(f'Duplicate key {repr(k)}?')
            hparams[k] = v
        # __dict__ OK, as we want instance-only properties
        for k, v in self.__dict__.items():
            if isinstance(v, ConfigurableObject) and v is not root:
                v._argparse_hparams(root, prefix + k + '-', hparams)


    @classmethod
    def _argparse_create(cls, env_prefix, prefix, args):
        if cls.config_defaults is not None:
            for k, v in cls.config_defaults.items():
                # Overwrite values in args which were not set.
                cls._argparse_check_env(env_prefix, prefix, k, args)
                args.setdefault(f'{prefix}{k}', v)
                # TODO I believe this is currently broken if a with_defaults()
                # is nested within another with_defaults().
        config = {}
        post_init = {}
        if cls.config is not None:
            assert issubclass(cls.config, pydantic.BaseModel)
            for k in cls.config.schema()['properties'].keys():
                if k.startswith('_'): continue
                docname = f'{prefix}{k}'
                v = args.pop(docname, None)
                if v is None:
                    # Check environment if wasn't specified otherwise
                    cls._argparse_check_env(env_prefix, prefix, k, args)
                    v = args.pop(docname, None)
                if v is not None:
                    config[k] = v
        for k in dir(cls):
            v = getattr(cls, k)
            if type(v) is type and issubclass(v, ConfigurableObject):
                post_init[k] = v._argparse_create(env_prefix, prefix + k + '-',
                        args)
        try:
            r = cls(config=config, child_configurables=post_init)
        except:
            raise TypeError(cls)
        return r


class _ConfigurableChildWithExtraHparams:
    def __init__(self, value, hparams):
        self.value = value
        self.hparams = hparams


class _ConfigurableSwitchImpl(ConfigurableObject):
    """A configurable switch statement, which alters available configuration.
    Reflected in `--help`.

    Example:

        >>> \
                class A(ConfigurableObject):
                    pass
                class B(ConfigurableObject):
                    pass
                class Obj(ConfigurableObject):
                    choice = ConfigurableSwitch({
                        'a': A,
                        'b': B,
                        'none': None,
                    }, default='none')
                Obj.argparse_create({'choice': 'a', 'choice-option': 99})
    """

    # These two overwritten by the `ConfigurableSwitch` method.
    _options = None
    _default = missing

    @property
    def v(self):
        return self._value


    def __init__(self, *, choice, value, is_ok=False):
        raise ValueError("Should not be instantiated directly.")


    @classmethod
    def _argparse_create(cls, env_prefix, prefix, args):
        choice = cls._default

        # `prefix` has hyphen; remove it
        choicename = prefix[:-1]
        v = args.pop(choicename, None)
        if v is None:
            cls._argparse_check_env(env_prefix, choicename, '', args)
            v = args.pop(choicename, None)
        if v is not None:
            choice = v

        if choice is missing:
            raise ValueError(f'Must specify {choicename}')

        value = cls._get_option(choice)
        if type(value) is type and issubclass(value, ConfigurableObject):
            value = value._argparse_create(env_prefix, prefix, args)

        return _ConfigurableChildWithExtraHparams(value,
                {choicename: choice})


    def _argparse_hparams(self, root, prefix, hparams):
        raise NotImplementedError("Shouldn't be called")


    @classmethod
    def _argparse_setup(cls, prefix, parser):
        name = prefix[:-1]

        # The tricky part -- figure out which switch has been requested, and
        # give help.
        choice_current = cls._default
        try:
            idx = sys.argv.index(f'--{name}')
            choice_current = sys.argv[idx+1]
        except ValueError:
            pass
        choice_name = 'no option'
        if choice_current is not missing:
            choice_name = repr(choice_current)

        # Now add help
        help = (f"Inferred {choice_name}; help shown corresponds to that "
                f"option. "
                f"Switch accepting: {repr(list(cls._options.keys()))}.")
        if cls._default is not missing:
            help += f' Default: {repr(cls._default)}.'
        help += (f' Pass another option to see available '
                f'arguments for that option.')
        parser.add_argument(f'--{name}', dest=name, help=help)

        if choice_current is not missing:
            value = cls._get_option(choice_current)
            if type(value) is type and issubclass(value, ConfigurableObject):
                value._argparse_setup(prefix, parser)


    @classmethod
    def _get_option(cls, choice):
        try:
            value = cls._options[choice]
        except KeyError:
            raise KeyError(f'Wanted {repr(choice)}; valid options: {list(cls._options.keys())}')
        return value


def ConfigurableSwitch(options, default: str=missing):
    return type('ConfigurableSwitch_Custom', (_ConfigurableSwitchImpl,),
            {'_options': options, '_default': default})

