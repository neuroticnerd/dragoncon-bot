# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import datetime
import json
import logging
import uuid
from collections import OrderedDict

import dateutil.parser

from sqlalchemy import Column, ForeignKey, create_engine, inspect, types
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import backref, relationship, sessionmaker

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


class ChoiceStringType(types.TypeDecorator):
    impl = types.String

    def __init__(self, choices, **kw):
        self.choices = list(choices)
        super(ChoiceStringType, self).__init__(**kw)

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
    def __tablename__(cls):  # noqa: N805
        return cls.__name__.lower()

    id = Column(types.Integer, primary_key=True, autoincrement=True)
    uuid = Column(AutoUUID)
    created = Column(types.DateTime, default=datetime.datetime.now)
    modified = Column(
        types.DateTime,
        default=datetime.datetime.now,
        onupdate=datetime.datetime.now
    )

    def dict(self, ordered=True):
        if ordered:
            obj = OrderedDict((
                (attr, getattr(self, attr)) for attr in self.column_names
            ))
        else:
            obj = {attr: getattr(self, attr) for attr in self.column_names}
        return obj

    @property
    def column_names(self):
        return inspect(self.__class__).columns.keys()

    def __str__(self):
        """ have to use json module otherwise OrderedDict has odd format """
        def value(val):
            if val.__class__.__module__ == 'builtins':
                return val
            return '{0}'.format(val)

        return json.dumps(OrderedDict((
            (attr, value(getattr(self, attr))) for attr in self.column_names
        )), indent=getattr(self, 'indent', None))


Model = declarative_base(cls=Base)


class Invocation(Model):
    debug = Column(types.Boolean)
    info = Column(types.Boolean)
    simple = Column(types.Boolean)
    use_cache = Column(types.Boolean)
    use_db = Column(types.Boolean)
    max_attempts = Column(types.Integer)
    max_price = Column(types.Integer)
    checkin = Column(types.Date, nullable=True)
    checkout = Column(types.Date, nullable=True)
    loglevel = Column(types.String(10))
    verbose = Column(types.Boolean)
    sms_enabled = Column(types.Boolean)
    email_enabled = Column(types.Boolean)

    def __init__(self, *args, **kwargs):
        self.checkin = self._check_date(kwargs.pop('checkin'))
        self.checkout = self._check_date(kwargs.pop('checkout'))
        super(Invocation, self).__init__(*args, **kwargs)

    def _check_date(self, value):
        if value is not None and not isinstance(value, datetime.date):
            return dateutil.parser.parse(value).date()
        return value


class ScrapeResultEntry(Model):
    HOST_HOTELS = get_host_names()

    invocation_id = Column(types.Integer, ForeignKey('invocation.id'))
    invocation = relationship(
        Invocation,
        backref=backref('results', uselist=True),
    )

    hotel = Column(ChoiceStringType(HOST_HOTELS))
    available = Column(types.Boolean, default=False)
    processed = Column(types.Boolean, default=False)
    error = Column(types.Boolean, default=False)
    traceback = Column(types.UnicodeText, nullable=True, default=None)
    post_process = Column(types.Boolean, default=False)
    raw = Column(types.UnicodeText)
    history = Column(types.UnicodeText)
    cookies = Column(types.UnicodeText)


_ENGINE = None
_SESSION_FACTORY = None


def init_database(db_url=None, db_filename=None):
    log = logging.getLogger(__name__)
    global _ENGINE
    global _SESSION_FACTORY
    db_filename = db_filename or 'dragonite.sqlite3'
    db_url = db_url or ('sqlite:///' + db_filename)
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


def object_session(obj):
    return _SESSION_FACTORY.object_session(obj)
