#!/usr/bin/env python
import os
import io
import sys
import shutil
from setuptools import setup, Command

about = {}

here = os.path.abspath(os.path.dirname(__file__))
with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

with open(os.path.join(here, 'bitmapist4', '__version__.py')) as f:
    exec(f.read(), about)


class UploadCommand(Command):
    """Support setup.py upload."""

    # If test option is set, the package is uploaded to test.pypi.org
    # and nothing is pushed to the git repository. In order to make
    # it work, you need to have a separate section [test] in your
    # ~/.pypirc.
    # More info on using testng PyPI server:
    # https://packaging.python.org/guides/using-testpypi/
    description = 'Build and publish the package.'
    user_options = [
        ('test', 't', "Upload package to the test server"),
    ]

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    def initialize_options(self):
        self.test = None

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status('Removing previous builds…')
            shutil.rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.status('Building Source and Wheel (universal) distribution…')
        os.system('{0} setup.py sdist bdist_wheel --universal'.format(
            sys.executable))

        self.status('Uploading the package to PyPi via Twine…')
        repo_string = ' --repository test' if self.test else ''
        os.system('twine upload {} dist/*'.format(repo_string))

        if not self.test:
            self.status('Pushing git tags…')
            os.system('git tag v{0}'.format(about['__version__']))
            os.system('git push --tags')

        sys.exit()


setup(
    name='bitmapist4',
    version=about['__version__'],
    description='Powerful analytics library using Redis bitmaps',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Doist Team",
    author_email="dev@doist.com",
    url="https://github.com/Doist/bitmapist4",
    install_requires=[
        'redis>=2.10',
        'future>=0.14',
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    packages=['bitmapist4'],
    include_package_data=True,
    platforms=["Any"],
    license="BSD",
    cmdclass={
        'upload': UploadCommand,
    },
    keywords='redis bitmap analytics bitmaps realtime cohort')
