from sqlalchemy import Column, Integer, ForeignKey, Table
from app.db.session import Base

# Many-to-Many relationship between TestSuite and TestCase
test_suite_cases = Table(
    'test_suite_cases',
    Base.metadata,
    Column('test_suite_id', Integer, ForeignKey('test_suites.id'), primary_key=True),
    Column('test_case_id', Integer, ForeignKey('test_cases.id'), primary_key=True)
)
