"""Integration tests for the moment.
"""

from pyobjconfig import PydanticBaseModel, ConfigurableObject, ConfigurableSwitch

import argparse
import os
import pydantic
import pytest
import typing

def test_basic():
    class BaseObject(ConfigurableObject):
        class config(PydanticBaseModel):
            a: int = 8
            b: str = 'hello world'

        def run(self):
            print(f'a: {self.config.a}, b: {self.config.b}')

    ap = argparse.ArgumentParser(description=__doc__)
    BaseObject.argparse_setup(ap)

    args = ap.parse_args([]).__dict__
    obj = BaseObject.argparse_create(args)
    obj.run()

    assert obj.config.a == 8
    assert obj.config.b == 'hello world'

    args = ap.parse_args(['--a', '99']).__dict__
    obj = BaseObject.argparse_create(args)
    assert obj.config.a == 99

    args = ap.parse_args(['--b', 'yodel']).__dict__
    obj = BaseObject.argparse_create(args)
    assert obj.config.b == 'yodel'

    with pytest.raises(SystemExit) as exc:
        args = ap.parse_args(['--a', 'yodel']).__dict__
        print(args)
        obj = BaseObject.argparse_create(args)


def test_default_none():
    """Ensure that an object with a default value of None MUST be overridden.
    """
    class A1(ConfigurableObject):
        class config(PydanticBaseModel):
            setting: int = None

    with pytest.raises(ValueError) as exc:
        A1.argparse_create({})
    assert 'Cannot leave parameters as `None`' in str(exc)

    A1.argparse_create({'setting': 8})


def test_enum():
    class A(ConfigurableObject):
        def get(self):
            return 'A'
    class B(ConfigurableObject):
        def get(self):
            return 'B'
    class Base(ConfigurableObject):
        child = ConfigurableSwitch({
            'a': A,
            'b': B,
        })

    with pytest.raises(ValueError) as exc:
        Base.argparse_create({})
    assert 'Must specify child' in str(exc.value)
    assert 'A' == Base.argparse_create({'child': 'a'}).child.get()
    assert 'B' == Base.argparse_create({'child': 'b'}).child.get()


def test_env():
    class Base(ConfigurableObject):
        class config(PydanticBaseModel):
            test: str = 'testing'
    old = os.environ
    try:
        os.environ = os.environ.copy()
        b = Base.argparse_create({}, env='BLEEP')
        assert b.config.test == 'testing'

        os.environ['BLEEP_TEST'] = 'yay!'

        b = Base.argparse_create({}, env='BLEEP')
        assert b.config.test == 'yay!'
        b = Base.argparse_create({}, env='BLEEP2')
        assert b.config.test == 'testing'
    finally:
        os.environ = old


def test_parse_types():
    '''Ensure that types coming from argparse are correct, rather than relying
    on pydantic.
    '''
    class A(ConfigurableObject):
        class config(PydanticBaseModel):
            a: int
            b: float
            c: typing.List[int]
            c2: typing.List[float]
            c3: typing.List[str]
            d: str

    ap = argparse.ArgumentParser()
    A.argparse_setup(ap)
    args = ap.parse_args(['--a', '1', '--b', '2', '--c', '[1, 2, 3]',
            '--c2', '1., 2.5, 3', '--c3', 'a,', '--c3', 'b', '--d', '4'])
    assert args.a == 1
    assert isinstance(args.a, int)

    assert args.b == 2
    assert isinstance(args.b, float)

    assert args.c == [1, 2, 3]
    assert isinstance(args.c, list)
    assert isinstance(args.c[0], int)

    assert args.c2 == [1., 2.5, 3.]
    assert isinstance(args.c2, list)
    assert isinstance(args.c2[0], float)

    assert args.c3 == ['a,', 'b']

    assert args.d == '4'
    assert isinstance(args.d, str)


def test_prefix():
    class A(ConfigurableObject):
        class B(ConfigurableObject):
            class config(PydanticBaseModel):
                lr_value: float = 1

    ap = argparse.ArgumentParser(description=__doc__)
    A.argparse_setup(ap)

    with pytest.raises(SystemExit):
        A.argparse_create(ap.parse_args(['--B-lr', '8']).__dict__)

