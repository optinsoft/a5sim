from distutils.core import setup
import re

s = open('a5sim/version.py').read()
v = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", s, re.M).group(1)

setup(name='a5sim',
    version=v,
    description='Async API wrapper for 5sim.net',
    install_requires=["aiohttp","certifi"],
    author='optinsoft',
    author_email='optinsoft@gmail.com',
    keywords=['5sim','sms','async'],
    url='https://github.com/optinsoft/a5sim',
    packages=['a5sim']
)
