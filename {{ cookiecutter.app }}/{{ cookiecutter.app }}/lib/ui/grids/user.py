from ics.html.grid import DynamicGrid, Column

from {{ cookiecutter.app }} import dao


def get_team_grid():
    """ Membres de l'équipe """

    headers = [
        Column("Prénom", 75),
        Column("Nom", 75),
    ]
    rows = [[u.first_name, u.last_name] for u in dao.get_active_users()]

    return DynamicGrid(
        rows, headers, height=500, dynamic=True, bootstrap=True, striped=True
    )
