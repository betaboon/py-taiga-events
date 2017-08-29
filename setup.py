import ast
import os
import re
from setuptools import find_packages, setup


with open('taiga_events/__init__.py', 'rb') as f:
    VERSION = str(ast.literal_eval(re.search(
        r'__version__\s+=\s+(.*)',
        f.read().decode('utf-8')).group(1)))


def _read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    return open(path).read()


setup(
    name='taiga-events',
    version=VERSION,
    description=('Python Implementation of Taiga-events'),
    long_description=_read('README.md'),
    url='https://github.com/betaboon/py-taiga-events',
    author='betaboon',
    author_email='betaboon@0x80.ninja',
    packages=find_packages('.'),
    package_dir={'taiga_events': 'taiga_events'},
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'taiga-events=taiga_events.cli:main',
        ]
    },
    install_requires=[
        'websockets',
        'aioamqp',
    ],
    test_suite='nose.collector',
    test_require=['nose'],
)
