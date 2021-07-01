# Python Installation Steps

## Windows
* Miniconda is recommended for installing Python on Windows
   * Download Miniconda Python 3.7 or later (https://docs.conda.io/en/latest/miniconda.html)
   * Run the downloaded Miniconda exe file, and accept all the defaults
   * Once installed, search in your windows start menu (press Windows Button + S) for "miniconda".
   * Click on the item named "Anaconda Prompt (miniconda3)"
   * Type "`where python`" to confirm that the Python you are using is in a "miniconda3" folder
   * Run the above "pip install ..." command

## Linux
* Run "`python3 --version`" to check which version of Python is already installed.  Python 3.7 or later is required.
   * If not installed, run "`sudo apt install python3`"
* If you get an error when running the above "pip install ..." command, try installing swig, which is a dependency of pyscard (dependency of pysim)
   * Run "`sudo apt install swig`"
   * Then rerun the above "pip install ..." command again
