"""
pygapi setup package
based on https://github.com/pypa/sampleproject/blob/master/setup.py
"""

from codecs import open
from os import path
from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='google-api-helper',
    version='0.1.2',

    description='Python helper class to streamlime interaction with Google APIs. Based on python-google-api-client.',
    long_description=long_description,
    url='https://github.com/paulwoelfel/pygapi',

    # Author details
    author='Paul Woelfel',
    author_email='paul.woelfel@zirrus.eu',

    # Choose your license
    license='GNU GPL v3',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries',

        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    keywords='google api python',

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    #   py_modules=["my_module"],

    install_requires=['google-api-python-client'],

    extras_require={
        'dev': [],
        'test': [],
    },

    package_data={},

    data_files=[],

    # entry_points={
    #     'console_scripts': [
    #         'sample=sample:main',
    #     ],
    # },
)
