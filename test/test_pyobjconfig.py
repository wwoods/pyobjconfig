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

    with pytest.raises(TypeError) as exc:
        args = ap.parse_args(['--a', 'yodel']).__dict__
        print(args)
        obj = BaseObject.argparse_create(args)


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


def test_list():
    class A(ConfigurableObject):
        class config(PydanticBaseModel):
            thing: typing.List[int] = [1]

    ap = argparse.ArgumentParser(description=__doc__)
    A.argparse_setup(ap)

    args = A.argparse_create(ap.parse_args([]).__dict__)
    assert args.config.thing == [1]
    args = A.argparse_create(ap.parse_args(['--thing', '2', '--thing', '3']).__dict__)
    assert args.config.thing == [2, 3]

