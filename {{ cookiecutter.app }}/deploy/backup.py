#!/usr/bin/env python

import os

os.chdir('/mnt/backup/')
os.system('tar zcvf docs.tgz /opt/{{ cookiecutter.app }}_docs')
print('--done')
