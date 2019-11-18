from invoke import task
from fabric import Connection
from glob import glob

HOSTS = {
    'demo': 'serv-ics-recette',
    'prod': '{{ cookiecutter.server_prod }}',
}


def _do(env, action):

    tarball = glob('dist/*')[0].split('/')[-1]
    c = Connection(host=HOSTS[env], user='devics')
    c.put('dist/{}'.format(tarball), remote='/tmp/%s' % (tarball,))
    c.put('deploy/{}_{}.py'.format(action, env), remote='/tmp/install.py')
    c.run('python3 /tmp/install.py --tarball {}'.format(tarball))
    c.run('rm /tmp/install.py')
    c.run('rm /tmp/{}'.format(tarball))


@task
def deploy(ctx, env):

    _do(env, 'deploy')


@task
def update(ctx, env):

    _do(env, 'update')
