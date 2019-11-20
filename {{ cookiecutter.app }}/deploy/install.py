import os
import sys
import subprocess
import logging
import argparse

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('install {{ cookiecutter.app }}')


DIRS = {{ cookiecutter.dirs }}

PACKAGES = set((
    # installed by default
    'libldap2-dev', 'libpq-dev', 'libsasl2-dev', 'postgresql-client',
    'libjpeg-dev', 'libfreetype6-dev', 'libz-dev', 'nginx', 'supervisor',
    'python-dev', 'python3-pip', 'python3-venv'))
{% if cookiecutter.use_odbc|int -%}
PACKAGES = PACKAGES.union((
    'unixodbc', 'unixodbc-dev',
    'freetds-common', 'freetds-bin', 'tdsodbc', 'g++'))
{% endif -%}
{% if cookiecutter.use_redis|int -%}
PACKAGES.add('redis-server')
{% endif -%}
{% if cookiecutter.use_r|int -%}
PACKAGES.add('r-base')
PACKAGES.add('r-base-dev')
R_PACKAGES = {{ cookiecutter.r_packages }}
{% endif %}


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


def get_user(context):
    if context == 'test':
        return 'gitlab-runner'
    else:
        return 'web'


def create_user():

    banner("Installation de l'utilsateur web")
    log.info('checking  account')
    users = [x.split(':')[0] for x in open('/etc/group', 'r').read().split('\n')]
    if 'web' not in users:
        sudo('groupadd web')
        sudo('useradd -m -g web -s /bin/bash web')
    else:
        log.info('already created')


def create_dirs():

    banner('Directories')
    for d in DIRS:
        if not os.path.exists(d):
            log.info('creating dir %s', d)
            sudo("mkdir %s && sudo chown -R web.web %s" % (d, d))


def install_debian_packages():
    banner('Debian packages')
    sudo("apt-get update")
    sudo('apt-get install -y --force-yes {}'.format(' '.join(PACKAGES)))


def install_r_packages():

    banner('R')
    repo = "http://mirror.ibcp.fr/pub/CRAN/"
    lines = subprocess.check_output("Rscript -e 'installed.packages()'", shell=True)
    lines = lines.decode()
    lines = lines.split('\n')
    installed = [l.split()[0] for l in lines[1:-1]]
    for pkg in R_PACKAGES:
        done = False
        if pkg.startswith('https://'):
            # specific version
            tgz = pkg.split('/')[-1]
            mod = tgz.split('_')[0]
            if mod not in installed:
                sudo('wget %s' % pkg)
                sudo('R CMD INSTALL %s' % (tgz,))
                os.unlink(tgz)
                done = True
        elif pkg not in installed:
            sudo("""Rscript -e 'install.packages("%s", repos="%s")'"""
                % (pkg, repo))
            done = True
        if not done:
            log.info('r package %s already installed', pkg)


def install_venv(context):

    banner('Virtual environment')
    if not os.path.exists('/opt/env3/{{ cookiecutter.app }}'):
        sudo('python3 -m venv /opt/env3/{{ cookiecutter.app }}')
        cmd = 'chown -R {}.{} /opt/env3/{{ cookiecutter.app }}'
        user = get_user(context)
        sudo(cmd.format(user, user))
    else:
        log.info('virtualenv already created')


def _install_sources_dev():
    """ en dev, on fait un lien symbolique """

    banner('Sources of {{ cookiecutter.app }}')
    if not os.path.exists('/opt/{{ cookiecutter.app }}'):
        sudo('ln -s /ics_src/{{ cookiecutter.app }} /opt/{{ cookiecutter.app }}')
    run_as('web',
        "cd /opt/{{ cookiecutter.app }} && /opt/env3/{{ cookiecutter.app }}/bin/python setup.py develop")


def _install_sources_test():
    """ en test, on fait un lien symbolique vers git repo """

    if not os.path.exists('/opt/{{ cookiecutter.app }}'):
        sudo('ln -s %s /opt/{{ cookiecutter.app }}' % os.path.abspath(os.path.curdir))
    run_as('gitlab-runner',
        "cd /opt/{{ cookiecutter.app }} && /opt/env3/{{ cookiecutter.app }}/bin/python setup.py develop")


def _install_sources_package(tarball):
    """ en demo/prod: install du package tgz """

    banner('Sources of {{ cookiecutter.app }}')
    if os.path.exists('/opt/{{ cookiecutter.app }}'):
        sudo('rm -rf /opt/{{ cookiecutter.app }}')
    call('cd /tmp && sudo tar zxvf {} -C /opt'.format(tarball))
    oldname = os.path.join('/opt', tarball.replace('.tar.gz', ''))
    sudo('mv %s %s' % (oldname, '/opt/{{ cookiecutter.app }}'))
    sudo('chown -R web.web /opt/{{ cookiecutter.app }}')
    run_as('web',
        "cd /opt/{{ cookiecutter.app }} && /opt/env3/{{ cookiecutter.app }}/bin/python setup.py develop")


def install_sources(context, tarball):
    if context == 'dev':
        _install_sources_dev()
    elif context == 'test':
        _install_sources_test()
    else:
        _install_sources_package(tarball)


def install_python_libs(context):

    user = get_user(context)
    run_as(user, '/opt/env3/{{ cookiecutter.app }}/bin/pip install -U setuptools pip==9.0.3')

    if context in ('dev', 'test'):
        banner('Python dev libs')
        req = '/opt/{{ cookiecutter.app }}/deploy/requirements-dev.txt'
        if os.path.exists(req):
            run_as(user, '/opt/env3/{{ cookiecutter.app }}/bin/pip install -U -r %s' % req)

    banner('Python libs')
    req = '/opt/{{ cookiecutter.app }}/deploy/requirements.txt'
    run_as(user, '/opt/env3/{{ cookiecutter.app }}/bin/pip install -U -r %s' % (req, ))


def install_nginx(context):

    banner('Nginx')
    default_conf = '/etc/nginx/sites-enabled/default'
    if os.path.exists(default_conf):
        sudo('rm %s' % default_conf)

    # set nginx user to web
    with open('/etc/nginx/nginx.conf', 'r') as ng:
        ngconf = ng.read()
    sudo('chmod o+w /etc/nginx/nginx.conf')
    with open('/etc/nginx/nginx.conf', 'w') as ng:
        ng.write(ngconf.replace('user www-data', 'user web'))
    sudo('chmod o-w /etc/nginx/nginx.conf')

    src = '/opt/{{ cookiecutter.app }}/deploy/nginx_{}'.format(context)
    dst = '/etc/nginx/sites-enabled/{{ cookiecutter.app }}.conf'
    if not os.path.islink(dst):
        sudo('ln -s %s %s' % (src, dst))

    src = '/opt/{{ cookiecutter.app }}/deploy/htpasswd'
    dst = '/etc/nginx/htpasswd'

    if os.path.exists(src) and not os.path.islink(dst):
        sudo('ln -s %s %s' % (src, dst))

    for x in ('cert', 'key'):
        src = '/opt/{{ cookiecutter.app }}/deploy/{}.pem'.format(x)
        dst = '/etc/nginx/{}.pem'.format(x)
        if os.path.exists(src) and not os.path.islink(dst):
            sudo('ln -s %s %s' % (src, dst))


def install_supervisor(context):

    dst = '/etc/supervisor/conf.d/{{ cookiecutter.app }}.conf'
    if not os.path.islink(dst):
        cmd = 'ln -s /opt/{{ cookiecutter.app }}/deploy/supervisor_{}.conf {}'
        sudo(cmd.format(context, dst))


def install_odbc():

    banner('ODBC')
    configs = {
        '/etc/odbc.ini': '/opt/{{ cookiecutter.app }}/deploy/odbc.ini',
        '/etc/freetds/freetds.conf': '/opt/{{ cookiecutter.app }}/deploy/freetds_dev.conf',
        '/etc/odbcinst.ini': '/opt/{{ cookiecutter.app }}/deploy/odbcinst.ini'
    }
    for (dst, src) in configs.items():
        if os.path.exists(dst):
            sudo('rm %s' % dst)
        if not os.path.islink(dst):
            sudo('ln -s %s %s' % (src, dst))


def run_migrations(context):

    user = get_user(context)
    if context in ('demo', 'prod'):
        db_env = ''
    elif context == 'test':
        db_env = 'DB_IP=localhost'
    elif context == 'dev':
        db_env = 'DB_IP={}'.format(input('>> adresse de la base de dev ? '))

    app_env = '{{ cookiecutter.app|upper }}_CONTEXT={}'.format(context)
    alembic = '/opt/env3/{{ cookiecutter.app }}/bin/alembic'
    cmd = 'cd /opt/{{ cookiecutter.app }} && {} {} {} upgrade head'
    banner('Migrations')
    run_as(user, cmd.format(db_env, app_env, alembic))


def restart():
    banner('Restart')
    sudo('service nginx restart')
    banner('SUCCESS - installation complete')


def deploy(context, tarball):

    banner('Déploiement de {{ cookiecutter.app }} en {}'.format(context))
    if context in ("dev", "demo", "prod"):
        create_user()
    create_dirs()
    install_debian_packages()
    {% if cookiecutter.use_r|int -%}
    install_r_packages()
    {% endif -%}
    install_venv(context)
    install_sources(context, tarball)
    install_python_libs(context)
    if context in ("dev", "demo", "prod"):
        install_nginx(context)
    if context in ("demo", "prod"):
        install_supervisor(context)
    {% if cookiecutter.use_odbc|int -%}
    install_odbc()
    {% endif -%}
    if context in ("test", "demo", "prod"):
        run_migrations(context)
    restart()


def update(context, tarball):

    banner('Update de {{ cookiecutter.app }} en {}'.format(context))
    install_sources(context, tarball)
    if context in ("test", "demo", "prod"):
        run_migrations(context)
    restart()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tarball", help="tarball à déployer", default="")
    parser.add_argument("--context", help="contexte d'execution (test, dev, demo, prod)")
    parser.add_argument("--action", help="action (deploy, update)")
    args = parser.parse_args()

    assert args.action in ('deploy', 'update')
    assert args.context in ('test', 'dev', 'demo', 'prod')
    if args.action == "deploy":
        deploy(args.context, args.tarball)
    elif args.action == "update":
        update(args.context, args.tarball)


if __name__ == '__main__':
    main()
