import setuptools

requirements_files = ["requirements.txt"]
required_packages = []
for req_filename in requirements_files:
    with open(req_filename) as f:
        required_packages.extend(f.read().splitlines())

setuptools.setup(
    name="sim_csv_script",
    version="1.3.3",
    description="Program SIM cards by importing CSV file",
    packages=setuptools.find_packages("src"),
    package_dir={"": "src"},
    url="",
    author="Andrew Ma",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
        "Operating System :: OS Independent",
        "Topic :: System :: Hardware :: Universal Serial Bus (USB) :: Smart Card",
        "Intended Audience :: Telecommunications Industry"
    ],
    python_requires=">=3.6",
    install_requires=required_packages,
    entry_points={
        "console_scripts": [
            "sim_csv_script = sim_csv_script.app:main"
        ]
    },
)
