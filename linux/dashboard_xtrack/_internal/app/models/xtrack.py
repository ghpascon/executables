"""
RFID models for SMARTX Connector.

Defines the Tag and Event models for storing RFID reader data
with proper indexing and relationships.
"""

from sqlalchemy import DateTime

try:
	from sqlalchemy import Column, Integer, String, Boolean
except ImportError as e:
	raise ImportError(
		'SQLAlchemy is required. Please install it with: pip install sqlalchemy'
	) from e

from .mixin import Base, BaseMixin

# timestamps
import pytz
from datetime import datetime


class Locations(Base, BaseMixin):
	__tablename__ = 'locations'

	# Primary key
	id = Column(Integer, primary_key=True, index=True)
	name = Column(String(255), nullable=True)

	def get_brazil_time():
		tz = pytz.timezone('America/Sao_Paulo')
		return datetime.now(tz)

	created_at = Column(
		DateTime(timezone=True),
		default=get_brazil_time,
		nullable=False,
	)

	updated_at = Column(
		DateTime(timezone=True),
		default=get_brazil_time,
		onupdate=get_brazil_time,
		nullable=False,
	)


class Objects(Base, BaseMixin):
	__tablename__ = 'objects'

	# Primary key
	idcode = Column(String(50), primary_key=True, nullable=False)
	active = Column(Boolean, nullable=True, default=True)
	location_id = Column(Integer, nullable=False)
	description = Column(String(255), nullable=True)
	last_seen = Column(DateTime(timezone=True), nullable=True)
	home_location_id = Column(Integer, nullable=True)
	last_modified = Column(DateTime(timezone=True), nullable=True)
	last_location = Column(DateTime(timezone=True), nullable=True)

	def get_brazil_time():
		tz = pytz.timezone('America/Sao_Paulo')
		return datetime.now(tz)

	created_at = Column(
		DateTime(timezone=True),
		default=get_brazil_time,
		nullable=False,
	)

	updated_at = Column(
		DateTime(timezone=True),
		default=get_brazil_time,
		onupdate=get_brazil_time,
		nullable=False,
	)


class Movements(Base, BaseMixin):
	__tablename__ = 'movements'

	# Primary key
	id = Column(Integer, primary_key=True, index=True)
	object_idcode = Column(String(50), nullable=False)
	from_location_id = Column(Integer, nullable=True)
	to_location_id = Column(Integer, nullable=True)

	def get_brazil_time():
		tz = pytz.timezone('America/Sao_Paulo')
		return datetime.now(tz)

	created_at = Column(
		DateTime(timezone=True),
		default=get_brazil_time,
		nullable=False,
		index=True,
	)

	updated_at = Column(
		DateTime(timezone=True),
		default=get_brazil_time,
		onupdate=get_brazil_time,
		nullable=False,
		index=True,
	)
