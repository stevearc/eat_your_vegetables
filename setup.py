""" Setup file """
from setuptools import setup, find_packages

import os


HERE = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(HERE, 'README.rst')).read()
CHANGES = open(os.path.join(HERE, 'CHANGES.txt')).read()

REQUIREMENTS = [
    'PyYAML',
    'six',
    'celery',
]

setup(
    name='eat_your_vegetables',
    version='0.0.0',
    description='Organizational framework for celery',
    long_description=README + '\n\n' + CHANGES,
    classifiers=[
        'Programming Language :: Python',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
    ],
    license='MIT',
    author='Steven Arcangeli',
    author_email='stevearc@stevearc.com',
    url='',
    zip_safe=True,
    include_package_data=True,
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'nom-worker = eat_your_vegetables:worker',
            'nom-beat = eat_your_vegetables:beat',
            'nom-flower = eat_your_vegetables:flower',
        ],
    },
    install_requires=REQUIREMENTS,
    tests_require=REQUIREMENTS,
)
