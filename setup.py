import os
import setuptools

with open('README.md') as f:
    long_desc = f.read()

with open('requirements.txt') as f:
    reqs = f.read().splitlines()

setuptools.setup(
        name='pyobjconfig',
        version='0.1.0',
        author='Walt Woods',
        author_email='woodswalben@gmail.com',
        description="An argparse+pydantic-based configuration system for Python.",
        long_description=long_desc,
        long_description_content_type='text/markdown',
        url='https://github.com/wwoods/pyobjconfig',
        packages=setuptools.find_packages(),
        install_requires=reqs,
)

