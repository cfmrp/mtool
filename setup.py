import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mtool",
    version="0.1",
    author="Stephan Oepen",
    author_email="oe@ifi.uio.no",
    description="Software to Manipulate Different Flavors of Semantic Graphs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cfmrp/mtool",
    packages=setuptools.find_packages(),
    py_modules=["graph", "analyzer", "treewidth"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
