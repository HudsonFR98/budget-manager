import os
os.chdir('docs')
os.system("sphinx-quickstart.exe -q -p {{ cookiecutter.app }} -a ics -v 0.0.1 docs")
