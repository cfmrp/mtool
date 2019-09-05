import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()


exec(open('version.py').read())
release = __version__
version = '.'.join(release.split('.')[:2])


setuptools.setup(
    name="mtool",
    version="0.0.1",
    author="Stephan Oepen <oe@ifi.uio.no>, Marco Kuhlmann <marco.kuhlmann@liu.se>, "
           "Daniel Hershcovich <daniel.hershcovich@gmail.com>, Tim O'Gorman <timjogorman@gmail.com>",
    author_email="mrp-organizers@nlpl.eu",
    description="The Swiss Army Knife of Meaning Representation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cfmrp/mtool",
    packages=setuptools.find_packages(),
    py_modules=["graph", "analyzer", "inspector", "treewidth", 'main', 'version'],
    license='LGPL-3.0',
    install_requires=[
        'numpy',
    ],
    entry_points = {
        'console_scripts': ['mtool=main:main'],
    },
    classifiers=[
        "Environment :: Console",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Information Analysis"
    ]
)
