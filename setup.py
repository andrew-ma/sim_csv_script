import setuptools

with open("requirements.txt") as f:
    required_packages = f.read().splitlines()

setuptools.setup(
    name="sim_csv_script",
    version="1.0.0",
    description="Program SIM cards by importing CSV file",
    packages=setuptools.find_packages(),
    url="https://github.com/andrew-ma/sim_csv_script",
    author="Bob",
    author_email="test@test.com",
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
        "Topic :: System :: Hardware :: Universal Serial Bus (USB) :: Smart Card",
    ],
    python_requires=">=3.7",
    install_requires=required_packages,
    entry_points={
        "console_scripts": [
            "sim_csv_script = sim_csv_script.app:main",
        ]
    },
)
