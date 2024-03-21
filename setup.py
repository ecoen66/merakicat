#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('HISTORY.md') as history_file:
    history = history_file.read()

requirements = [
    "webexteamsbot==0.1.4.2",
    "webexteamssdk==1.0.3",
    "Flask>=0.12.1",
    "netmiko==4.3.0",
    "tabulate==0.9.0",
    "ciscoconfparse2==0.5",
    "meraki==1.42.0",
    "ngrok==1.1.0",
    "python-docx==1.1.0",
    "docx2pdf==0.1.8",
    "requests==2.31.0"
    ]

setup_requirements = [ ]

setup(
    author="Ed Coen",
    author_email='ecoen@cisco.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3 :: Only',
    ],
    description="An app to check and translate Catalyst switch configs to Meraki.",
    install_requires=requirements,
    license="MIT license",
    long_description_content_type="text/markdown",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='merakicat,catalyst,meraki,cisco,migration,webexteamsbot',
    name='merakicat',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    setup_requires=setup_requirements,
    url='https://github.com/ecoen66/merakicat',
    zip_safe=False,
)
