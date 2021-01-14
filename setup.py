import os
import setuptools

with open('README.md') as f:
    long_desc = f.read()

setuptools.setup(
        name='pyobjconfig',
        version='0.1.2',
        author='Walt Woods',
        author_email='woodswalben@gmail.com',
        description="An argparse+pydantic-based configuration system for Python.",
        long_description=long_desc,
        long_description_content_type='text/markdown',
        url='https://github.com/wwoods/pyobjconfig',
        packages=setuptools.find_packages(),
        install_requires=['pydantic'],
)

