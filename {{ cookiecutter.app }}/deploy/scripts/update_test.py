import os
import sys
import subprocess
import logging
import argparse

# ATTENTION: ce script est genere automatiquement par la librairie ics_deploy
# et le script /deploy/create_install_scripts.py de votre application.
# Ne pas le changer a la main, mais relancer create_install_scripts.

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('install {{ cookiecutter.app }}')
parser = argparse.ArgumentParser()
parser.add_argument("--tarball", help="tarball to deploy", default='')
args = parser.parse_args()
tarball = args.tarball

def call(cmd):

    log.info(cmd)
    subprocess.check_call(cmd, shell=True)


def run_as(user, cmd):

    full_cmd = 'su - %s -c "%s"' % (user, cmd)
    sudo(full_cmd)


def sudo(cmd):

    full_cmd = 'sudo ' + cmd
    call(full_cmd)


def banner(msg):
    log.info('************************************************************')
    log.info('** %s ', msg)
    log.info('************************************************************')

banner('Start installation of {{ cookiecutter.app }} in test mode')

banner('Sources of {{ cookiecutter.app }}')

if not os.path.exists('/opt/{{ cookiecutter.app }}'):
    sudo('ln -s %s /opt/{{ cookiecutter.app }}' % os.path.abspath(os.path.curdir))

run_as('gitlab-runner',
    "cd /opt/{{ cookiecutter.app }} && /opt/env3/{{ cookiecutter.app }}/bin/python setup.py develop")
db_env = 'DB_IP=localhost'


banner('Migrations')

run_as('gitlab-runner',
    'cd /opt/{{ cookiecutter.app }} && %s GOSUB_CONTEXT=test /opt/env3/{{ cookiecutter.app }}/bin/alembic upgrade head' % db_env)



banner('SUCCESS - installation complete')
