import os

from setuptools import find_packages, setup


def prerelease_local_scheme(version):
    """Return local scheme version unless building on master in CircleCI.
    This function returns the local scheme version number
    (e.g. 0.0.0.dev<N>+g<HASH>) unless building on CircleCI for a
    pre-release in which case it ignores the hash and produces a
    PEP440 compliant pre-release version number (e.g. 0.0.0.dev<N>).
    """
    from setuptools_scm.version import get_local_node_and_date

    if os.getenv('CIRCLE_BRANCH') == 'master':
        return ''
    else:
        return get_local_node_and_date(version)


with open('README.rst') as f:
    readme = f.read()

# perform the install
setup(
    name='girder-slicer-cli-web',
    use_scm_version={
        'local_scheme': prerelease_local_scheme,
        'fallback_version': 'development'},
    setup_requires=[
        'setuptools-scm<7 ; python_version < "3.7"',
        'setuptools-scm ; python_version >= "3.7"',
    ],
    description='A girder plugin for exposing slicer CLIs over the web',
    long_description=readme,
    long_description_content_type='text/x-rst',
    url='https://github.com/girder/slicer_cli_web',
    keywords='girder-plugin, slicer_cli_web',
    author='Kitware, Inc.',
    author_email='kitware@kitware.com',
    license='Apache Software License 2.0',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    include_package_data=True,
    package_dir={'girder_slicer_cli_web': 'slicer_cli_web'},
    packages=find_packages(exclude=['tests', 'test.*']),
    zip_safe=False,
    install_requires=[
        'ctk_cli',
        'jinja2',
        'jsonschema',
        'pyyaml',
        'importlib-metadata<5 ; python_version < "3.8"',
    ],
    extras_require={
        'girder': [
            'docker>=2.6.0',
            'girder>=3.0.4',
            'girder-jobs>=3.0.3',
            'girder-worker[girder]>=0.6.0',
        ],
        'worker': [
            'docker>=2.6.0',
            'girder-worker[worker]>=0.6.0',
        ]
    },
    entry_points={
        'girder.plugin': [
            'slicer_cli_web = slicer_cli_web.girder_plugin:SlicerCLIWebPlugin'
        ],
        'girder_worker_plugins': [
            'slicer_cli_web = slicer_cli_web.girder_worker_plugin:SlicerCLIWebWorkerPlugin'
        ]
    },
    python_requires='>=3.6',
)
