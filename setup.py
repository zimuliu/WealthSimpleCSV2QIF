from setuptools import setup, find_packages

setup(
    name='ws-csv-to-qif',
    version='0.1',
    packages=find_packages(),
    install_requires=[
    ],
    entry_points={
        'console_scripts': [
            'ws-csv-to-qif=app.main:main',
        ],
    },
)
