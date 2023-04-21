# pyobjconfig

`pyobjconfig` is a module suite designed with Machine Learning (ML) experiments in mind, but should work for a broad range of hierarchical configurations.

## Example usage

Pyobjconfig supports configuring nested objects, such that each object has control over its own configuration:

```python

import argparse
import pyobjconfig as poc

# Any class which plugs into pyobjconfig should derive from `ConfigurableObject`
class Child(poc.ConfigurableObject):
    # To register configuration options for this class, add a `config` member
    # which derives from a pydantic model.
    class config(poc.PydanticBaseModel):
        # Pydantic handles basic type validation and allows default values to be
        # set
        inner: str = 'hello'

class Base(poc.ConfigurableObject):
    class config(poc.PydanticBaseModel):
        hello: str = 'hi'

    # Assigning a class deriving from `ConfigurableObject` as a member of a
    # class definition results in a nested object, which will be instantiated
    # using parameters from the command line.
    child = Child

ap = argparse.ArgumentParser()
Base.argparse_setup(ap)

args = ap.parse_args(['--child-inner', 'beep']).__dict__
obj = Base.argparse_create(args)
print(obj.config.hello)  # Prints 'hi'
print(obj.child.config.inner)  # Prints 'beep'

ap.print_help()
# usage: ipython [-h] [--hello HELLO] [--child-inner CHILD-INNER]
#
# optional arguments:
#   -h, --help            show this help message and exit
#   --hello HELLO         Default: hi
#   --child-inner CHILD-INNER
#                         Default: hello

```

Switches are also supported, such that the class (or value) of a child member may be changed at initialization time. Additionally, the `--help` for the `argparse` parser will change to reflect the choice of child:

```python
import pyobjconfig as poc
class A(poc.ConfigurableObject):
    pass
class B(poc.ConfigurableObject):
    pass
class Base(poc.ConfigurableObject):
    child = poc.ConfigurableSwitch({
        'a': A,
        'b': B,
        'none': None,
    }, default='none')
```

Experimentally, environment variables are supported. Not yet well tested, but calling `argparse_create(args, env='PREFIX')` will allow e.g. `PREFIX_CHILD=a` to be specified in the environment. Arguments on the command line take precedence.

```python
import argparse
import pyobjconfig as poc
```

## Usage with pytorch

Pytorch overrides `__setattr__` in a way that is incompatible with the `ConfigurableObject` class provided by `pyobjconfig`. To work around this, use the `pyobjconfig.torch.ConfigurableModule` as a drop-in replacement for `torch.nn.Module`.


# Changelog
* 2023-04-21 - v0.1.4. `argparse.ArgumentParser` has `type` specified for each argument now, so local equality comparisons against previous `argparse_hparams()` before object instantiation will work.
* 2023-04-18 - v0.1.3. Disallow `None` as parameter values because it serializes poorly, and disallow abbreviated parameter matches to avoid confusion.
* 2021-01-14 - v0.1.2. Support lists on the command line.
