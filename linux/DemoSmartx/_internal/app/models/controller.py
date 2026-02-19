"""
RFID models for SMARTX Connector.

Defines the Tag and Event models for storing RFID reader data
with proper indexing and relationships.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean

from smartx_rfid.models import Base, BaseMixin


class Orders(Base, BaseMixin):
	__tablename__ = 'orders'

	# Primary key
	id = Column(Integer, primary_key=True, autoincrement=True)

	order = Column(String(100), nullable=False)
	tags = Column(Text, nullable=True)


class FinishedOrders(Base, BaseMixin):
	__tablename__ = 'finished_orders'

	# Primary key
	id = Column(Integer, primary_key=True, autoincrement=True)

	order = Column(String(100), nullable=False)
	tags = Column(Text, nullable=True)
	success = Column(Boolean, default=False, nullable=False)
