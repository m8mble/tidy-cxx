#!/usr/bin/env python3

import io
import re
from glob import glob
from os.path import basename, dirname, join, splitext
from setuptools import find_packages, setup


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()

def sub_all(pattern, replace, data):
    while True:
        data, num_replacements = re.subn(pattern, replace, data)
        if not num_replacements:
            return data

def clear_links(data):
    data = sub_all('\[!?[^\[\]]*\]\[.[^\[\]]+\]', '', data)
    data = [l for l in data.splitlines() if not re.match('^\[[^\[\]]+\]:\s+[^\s]+\s*$', l)]
    return '\n'.join(data)


setup(
    name='tidy-cxx',
    version='0.1',
    license='MIT License',
    description='Tools for Tidying up C/C++ Code',
    long_description=clear_links(read('README.md')),
    packages=find_packages('src'),
    exclude=['contrib', 'docs', 'tests'],

    author='m8mble',
    author_email='m8mble@vivaldi.net',
    url='https://github.com/m8mble/tidy-cxx',

    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',

        'Topic :: Software Development',
        'Topic :: Software Development :: Quality Assurance',

        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',

        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ],
    keywords=['tidy'],
    install_requires=[],
    extras_require={
        # 'dev': ['check-manifest'],
        'test': ['pytest'],
    }
)


