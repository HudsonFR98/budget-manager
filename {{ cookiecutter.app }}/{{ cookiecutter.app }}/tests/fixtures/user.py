from {{ cookiecutter.app }}.model import models


DATA = {
    models.User: [
        dict(
            last_name=u'Selloum',
            has_left=0,
            first_name=u'Mohammed',
            id=1,
            pwd=u'test',
            ide=u'selloum',
            ptf_id=3,
            email=u'amoro@igbmc.fr',
            center_id=1
        ),
    ],
}