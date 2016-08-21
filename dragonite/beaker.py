# -*- encoding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import logging
import uuid

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy import create_engine
from sqlalchemy import types
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship, backref

from .scrapers import get_host_names


class AutoUUID(types.TypeDecorator):
    """
    Platform-independent Auto-UUID type.
    *** slightly modified version of GUID example in sqlalchemy docs ***

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    """
    impl = types.CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            dtype = dialect.type_descriptor(postgresql.UUID())
        else:
            dtype = dialect.type_descriptor(types.CHAR(32))
        return dtype

    def process_bind_param(self, value, dialect):
        if value is None:
            # auto-create a uuid if one was not provided
            value = uuid.uuid4()

        if dialect.name == 'postgresql':
            bound = str(value)
        elif not isinstance(value, uuid.UUID):
            bound = '{0:32x}'.format(uuid.UUID(value).int)
        else:
            bound = '{0:32x}'.format(value.int)

        return bound

    def process_result_value(self, value, dialect):
        if value is None:
            raise ValueError('AutoUUID should never be None')
        return uuid.UUID(value)


class ChoiceType(types.TypeDecorator):
    impl = types.String

    def __init__(self, choices, **kw):
        self.choices = list(choices)
        super(ChoiceType, self).__init__(**kw)

    def process_bind_param(self, value, dialect):
        if value not in self.choices:
            raise ValueError('{0} is not a valid choice! {1}'.format(
                value, self.choices
            ))
        return '{0}'.format(value)

    def process_result_value(self, value, dialect):
        return value


class Base(object):
    @declared_attr
    def __tablename__(cls):  # NOQA
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(AutoUUID)
    created = Column(DateTime, default=datetime.now)
    modified = Column(DateTime, default=datetime.now, onupdate=datetime.now)


Model = declarative_base(cls=Base)


class Invocation(Model):
    settings = Column(String)


class ScrapeResultsEntry(Model):
    HOST_HOTELS = get_host_names()

    invocation_id = Column(Integer, ForeignKey('invocation.id'))
    invocation = relationship(
        Invocation,
        backref=backref('results', uselist=True),
    )

    hotel = Column(ChoiceType(HOST_HOTELS))
    available = Column(Boolean)
    processed = Column(Boolean, default=False)
    response = Column(String)


_ENGINE = None
_SESSION_FACTORY = None


def init_database(db_url=None, db_filename=None):
    log = logging.getLogger(__name__)
    global _ENGINE
    global _SESSION_FACTORY
    if db_filename is None:
        db_filename = 'dragonite.sqlite3'
    if db_url is None:
        db_url = 'sqlite:///' + db_filename
    _ENGINE = create_engine(db_url)
    _SESSION_FACTORY = sessionmaker()
    _SESSION_FACTORY.configure(bind=_ENGINE)
    Model.metadata.create_all(_ENGINE)
    log.debug('database initialization completed.')


def create_session():
    log = logging.getLogger(__name__)
    if _SESSION_FACTORY is None:
        raise ValueError(__name__ + '.init_database() must be called first!')
    session = _SESSION_FACTORY()
    log.debug('database session created.')
    return session
