from setuptools import setup

setup(
    name='pyfantasy',
    version='0.1',
    description='An unofficial API to view and modify a Yahoo Fantasy team.',
    url='http://github.com/ma-schmidt/pyfantasy',
    author='Marc-Antoine Schmidt',
    author_email='marc.a.schmidt@gmail.com',
    license='MIT',
    packages=['pyfantasy'],
    zip_safe=False,
    install_requires=[
      'xmltodict',
      'rauth',
      'pyyaml',
    ],
)
