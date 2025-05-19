#! /bin/bash


# we cant run pycodestyle directly in gitlab since the return code is !=0 and
# it does not generate artifacts
/opt/env3/fair3r_custom_overlay/bin/pycodestyle fair3r_custom_overlay > pep8.out
exit 0
