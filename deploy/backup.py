#!/usr/bin/env python

import os

os.chdir('/mnt/backup/')
os.system('tar zcvf docs.tgz /opt/fair3r_custom_overlay_docs')
print('--done')
