# Copyright (c) LinkedIn Corporation. All rights reserved. Licensed under the BSD-2 Clause license.
# See LICENSE in the project root for license information.

import setuptools

setuptools.setup(
    name='iris-frontend',
    version='0.1.0',
    package_dir={'': 'src'},
    packages=setuptools.find_packages('src'),
    include_package_data=True,
    install_requires=[
        'Flask==0.10.1',
        'Flask-Assets==0.10',
        'Flask-Login==0.3.0',
        'Jinja2==2.7.3',
        'PyYAML==3.11',
        'ujson==1.35',
        'webassets==0.10.1',
        'urllib3==1.10.1',
        'python-ldap==2.4.9',
        'cssmin==0.2.0',
    ],
    entry_points={
        'console_scripts': [
            'build_assets = iris_frontend.bin.build_assets:main',
        ]
    }
)
