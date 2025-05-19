import os
import sys
import subprocess
import logging
import argparse

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger('install fair3r_custom_overlay')


DIRS = ['/var/log/fair3r_custom_overlay', '/opt/fair3r_custom_overlay_docs']

PACKAGES = set((
    # installed by default
    'libldap2-dev', 'libpq-dev', 'libsasl2-dev', 'postgresql-client',
    'libjpeg-dev', 'libfreetype6-dev', 'libz-dev', 'nginx', 'supervisor',
    'python-dev', 'python3-pip', 'python3-venv'))



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
    if not os.path.exists('/opt/env3/fair3r_custom_overlay'):
        sudo('python3 -m venv /opt/env3/fair3r_custom_overlay')
        cmd = 'chown -R {}.{} /opt/env3/fair3r_custom_overlay'
        user = get_user(context)
        sudo(cmd.format(user, user))
    else:
        log.info('virtualenv already created')


def _install_sources_dev():
    """ en dev, on fait un lien symbolique """

    banner('Sources of fair3r_custom_overlay')
    run_as('web',
        "cd /opt/fair3r_custom_overlay && /opt/env3/fair3r_custom_overlay/bin/python setup.py develop")


def _install_sources_test():
    """ en test, on fait un lien symbolique vers git repo """

    if not os.path.exists('/opt/fair3r_custom_overlay'):
        sudo('ln -s %s /opt/fair3r_custom_overlay' % os.path.abspath(os.path.curdir))
    run_as('gitlab-runner',
        "cd /opt/fair3r_custom_overlay && /opt/env3/fair3r_custom_overlay/bin/python setup.py develop")


def _install_sources_package(tarball):
    """ en demo/prod: install du package tgz """

    banner('Sources of fair3r_custom_overlay')
    if os.path.exists('/opt/fair3r_custom_overlay'):
        sudo('rm -rf /opt/fair3r_custom_overlay')
    call('cd /tmp && sudo tar zxvf {} -C /opt'.format(tarball))
    oldname = os.path.join('/opt', tarball.replace('.tar.gz', ''))
    sudo('mv %s %s' % (oldname, '/opt/fair3r_custom_overlay'))
    sudo('chown -R web.web /opt/fair3r_custom_overlay')
    run_as('web',
        "cd /opt/fair3r_custom_overlay && /opt/env3/fair3r_custom_overlay/bin/python setup.py develop")


def install_sources(context, tarball):
    if context == 'dev':
        _install_sources_dev()
    elif context == 'test':
        _install_sources_test()
    else:
        _install_sources_package(tarball)


def install_python_libs(context):

    user = get_user(context)
    run_as(user, '/opt/env3/fair3r_custom_overlay/bin/pip install -U setuptools pip')

    if context in ('dev', 'test'):
        banner('Python dev libs')
        req = '/opt/fair3r_custom_overlay/deploy/requirements-dev.txt'
        if os.path.exists(req):
            run_as(user, '/opt/env3/fair3r_custom_overlay/bin/pip install -U -r %s' % req)

    banner('Python libs')
    req = '/opt/fair3r_custom_overlay/deploy/requirements.txt'
    run_as(user, '/opt/env3/fair3r_custom_overlay/bin/pip install -U -r %s' % (req, ))


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

    src = '/opt/fair3r_custom_overlay/deploy/nginx_{}'.format(context)
    dst = '/etc/nginx/sites-enabled/fair3r_custom_overlay.conf'
    if not os.path.islink(dst):
        sudo('ln -s %s %s' % (src, dst))

    src = '/opt/fair3r_custom_overlay/deploy/htpasswd'
    dst = '/etc/nginx/htpasswd'

    if os.path.exists(src) and not os.path.islink(dst):
        sudo('ln -s %s %s' % (src, dst))

    for x in ('cert', 'key'):
        src = '/opt/fair3r_custom_overlay/deploy/{}.pem'.format(x)
        dst = '/etc/nginx/{}.pem'.format(x)
        if os.path.exists(src) and not os.path.islink(dst):
            sudo('ln -s %s %s' % (src, dst))


def install_supervisor(context):

    dst = '/etc/supervisor/conf.d/fair3r_custom_overlay.conf'
    if not os.path.islink(dst):
        cmd = 'ln -s /opt/fair3r_custom_overlay/deploy/supervisor_{}.conf {}'
        sudo(cmd.format(context, dst))


def install_odbc():

    banner('ODBC')
    configs = {
        '/etc/odbc.ini': '/opt/fair3r_custom_overlay/deploy/odbc.ini',
        '/etc/freetds/freetds.conf': '/opt/fair3r_custom_overlay/deploy/freetds_dev.conf',
        '/etc/odbcinst.ini': '/opt/fair3r_custom_overlay/deploy/odbcinst.ini'
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

    app_env = 'FAIR3R_CUSTOM_OVERLAY_CONTEXT={}'.format(context)
    alembic = '/opt/env3/fair3r_custom_overlay/bin/alembic'
    cmd = 'cd /opt/fair3r_custom_overlay && {} {} {} upgrade head'
    banner('Migrations')
    run_as(user, cmd.format(db_env, app_env, alembic))


def restart():
    banner('Restart')
    sudo('service nginx restart')
    banner('SUCCESS - installation complete')


def deploy(context, tarball):

    banner('Déploiement de fair3r_custom_overlay en {}'.format(context))
    if context in ("dev", "demo", "prod"):
        create_user()
    create_dirs()
    install_debian_packages()
    install_venv(context)
    install_sources(context, tarball)
    install_python_libs(context)
    if context in ("dev", "demo", "prod"):
        install_nginx(context)
    if context in ("demo", "prod"):
        install_supervisor(context)
    if context in ("test", "demo", "prod"):
        run_migrations(context)
    restart()


def update(context, tarball):

    banner('Update de fair3r_custom_overlay en {}'.format(context))
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
