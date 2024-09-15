from setuptools import setup, find_packages

setup(
    name='custompythonlogger',
    version='1.0',
    packages=find_packages(),
    include_package_data=True,  # Include non-code files
    package_data={
        # Include JSON files in the 'config' folder
        'custompythonlogger.config': ['logging.json'],
    },
)
