from setuptools import setup

with open('requirements.txt') as f:
    required = f.read().splitlines()

with open('README.md') as f:
    long_desc = f.read()
    
setup(
    name='trovesync',
    version='0.1.0',
    author='Oeystein Kjaernet',
    author_email='kjarnet on gmail',
    packages=['trovesync'],
    url='http://github.com/kjarnet/trovesync',
    license='LICENSE.txt',
    description='Application for synchronizing a local folder with a trovebox.com album.',
    long_description=long_desc,
    install_requires=required
)

