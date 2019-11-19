import os
import sys
import subprocess
from . import shared


context = "prod"
shared.create_user()
shared.create_dirs()
shared.install_debian_packages()
{% if cookiecutter.use_r %}
shared.install_r_packages()
{% endif %}
shared.install_venv(context)
shared.install_sources(context)
shared.install_python_libs(context)
shared.install_nginx(context)
shared.install_supervisor(context)
{% if cookiecutter.use_odbc %}
shared.install_odbc()
{% endif %}
shared.run_migrations(context)
shared.restart()
