import ics_deploy

if __name__ == '__main__':

    dirs = (
        '/var/log/{{ cookiecutter.app }}',
        '/opt/{{ cookiecutter.app }}_docs',
    )

    ics_deploy.create_scripts('{{ cookiecutter.app }}', dirs=dirs)
