"""
Import all models to ensure they are registered with SQLAlchemy.
This is important for relationship resolution.
"""
from app.models.user import User
from app.models.project import Project
from app.models.module import Module
from app.models.page import Page
from app.models.element import PageElement
from app.models.case import TestCase
from app.models.suite import TestSuite
from app.models.report import TestReport
from app.models.associations import test_suite_cases

__all__ = [
    "User",
    "Project",
    "Module",
    "Page",
    "PageElement",
    "TestCase",
    "TestSuite",
    "TestReport",
    "test_suite_cases",
]
