# dummy for editable installs
from setuptools import find_packages
from setuptools import setup

setup(
    setup_requires=["pbr"],
    pbr=True,
    name="punchbox",
    entry_points={"console_scripts": ["punchbox = punchbox.cli:main"]},
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=["click", "mido", "pbr", "PyYAML", "svgwrite"],
)
