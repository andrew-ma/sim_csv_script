import setuptools

requirements_files = ["requirements.txt", "requirements_gui.txt"]
required_packages = []
for req_filename in requirements_files:
    with open(req_filename) as f:
        required_packages.extend(f.read().splitlines())

setuptools.setup(
    name="sim_csv_script",
    version="1.0.0",
    description="Program SIM cards by importing CSV file",
    packages=setuptools.find_packages(),
    url="",
    author="",
    author_email="",
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
            "sim_csv_gui = sim_csv_gui.app:main"
        ]
    },
)
