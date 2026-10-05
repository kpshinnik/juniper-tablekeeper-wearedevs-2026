"""Descriptions travel with every frozen JUnit result, including failing cases."""
import pytest


@pytest.fixture(autouse=True)
def evidence_description(request, record_property):
    record_property('description', (request.function.__doc__ or '').strip())
