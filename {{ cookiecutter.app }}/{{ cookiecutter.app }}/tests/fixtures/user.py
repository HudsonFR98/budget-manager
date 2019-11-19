from {{ cookiecutter.app }} import models


DATA = {
    models.User: [
        dict(
            last_name='Selloum',
            has_left=0,
            first_name='Mohammed',
            id=1,
            pwd='test',
            ide='selloum',
            ptf_id=3,
            email='selloum@igbmc.fr',
            center_id=1
        ),
    ],
}