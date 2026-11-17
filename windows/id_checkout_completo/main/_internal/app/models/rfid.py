"""
RFID models for SMARTX Connector.

Defines the Tag and Event models for storing RFID reader data
with proper indexing and relationships.
"""

from sqlalchemy import Column, Index, Integer, String, Text

from smartx_rfid.models import Base, BaseMixin


class Tag(Base, BaseMixin):
	"""
	RFID Tag model for storing tag read events.

	Stores information about RFID tags detected by readers,
	including EPC, TID, antenna, and signal strength data.
	"""

	__tablename__ = 'tags'
	__cleanup__ = True

	# Primary key
	id = Column(Integer, primary_key=True, autoincrement=True)

	# Device identification
	device = Column(String(100), nullable=False)

	# RFID data fields
	epc = Column(String(24), nullable=False, index=True)

	tid = Column(String(24), nullable=True, index=True)

	ant = Column(Integer, nullable=True)
	rssi = Column(Integer, nullable=True)


class Event(Base, BaseMixin):
	"""
	RFID Event model for storing system and reader events.

	Stores various types of events from RFID readers and the system,
	including errors, status changes, and operational events.
	"""

	__tablename__ = 'events'
	__cleanup__ = True

	# Primary key
	id = Column(Integer, primary_key=True, autoincrement=True)

	# Device identification
	device = Column(String(100), nullable=False, index=True)

	# Event classification
	event_type = Column(String(50), nullable=False, index=True)

	# Event data
	event_data = Column(Text, nullable=False)

	# Indexes for optimal query performance
	__table_args__ = (
		# Composite indexes
		Index('ix_events_device_type', 'device', 'event_type'),
	)
