import logging

from ics.db import sa
from ics.tests.util import with_collections
from ics.tests.util import load_collections as load
from ics.tests.util import unload_collections as unload

from {{ cookiecutter.app }}.lib.config import CONFIG
from {{ cookiecutter.app }} import models
from sqlalchemy import DDL


def connect():
    logging.basicConfig(level=CONFIG.LOG_LEVEL)
    # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    sa.open(CONFIG.SQLALCHEMY_DATABASE_URI)


def disconnect():
    sa.DBSession.remove()


def flush():
    sa.DBSession.rollback()
    models.AdminPcr.query.delete()
    models.PcrWell.query.delete()
    models.PCR.query.delete()
    models.Run.query.delete()
    models.MatingGenotypeAllele.query.delete()
    models.MatingGenotype.query.delete()
    models.Sample.query.delete()
    models.Batch.query.delete()
    models.MatingGenotype.query.delete()
    models.Mating.query.delete()
    models.Request.query.delete()
    models.MultiplexPairs.query.delete()
    models.OligoWellContent.query.delete()
    models.PairAlleles.query.delete()
    models.Multiplex.query.delete()
    models.OligoPair.query.delete()
    models.OligoSlide.query.delete()
    models.OligoPlate.query.delete()
    models.OligoSlidesStock.query.delete()
    models.Gene.query.delete()
    models.DNAPlate.query.delete()
    models.Allele.query.delete()
    models.Request.query.delete()
    models.User.query.delete()
    commit()


def expire():
    sa.DBSession.expire_all()


def commit():
    sa.DBSession.commit()


def rollback():
    sa.DBSession.rollback()