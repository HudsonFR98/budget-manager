from invoke import task
from fabric import Connection
from glob import glob

HOSTS = {
    'demo': 'serv-ics-recette',
    'prod': '{{ cookiecutter.server_prod }}',
}


@task
def install(ctx, action, env):

    tarball = glob('dist/*')[0].split('/')[-1]
    c = Connection(host=HOSTS[env], user='devics')
    c.put('dist/{}'.format(tarball), remote='/tmp/%s' % (tarball,))
    c.put('deploy/install.py', remote='/tmp/install.py')
    cmd = 'python3 /tmp/install.py --tarball {} --context {} --action {}'
    c.run(cmd.format(tarball, env, action))
    c.run('rm /tmp/install.py')
    c.run('rm /tmp/{}'.format(tarball))
