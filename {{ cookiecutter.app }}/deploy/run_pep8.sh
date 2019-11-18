#! /bin/bash


# we cant run pycodestyle directly in gitlab since the return code is !=0 and
# it does not generate artifacts
/opt/env3/{{ cookiecutter.app }}/bin/pycodestyle {{ cookiecutter.app }} > pep8.out
exit 0
