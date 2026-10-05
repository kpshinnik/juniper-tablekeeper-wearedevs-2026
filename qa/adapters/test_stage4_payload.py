"""Run original semantic assertions against the explicitly bound schema4 carrier.

These 49 executions alias existing definitions, adding no acceptance definitions.
Raw original selector failures remain preserved in their separate attempts.
"""
import pytest
from adapters import test_string_payload as old
from adapters.stage4_carrier import payload, seal, exported
from derived import test_stage3_integrity as integrity
from derived import test_additional_stage1 as additional
from derived.test_stage1 import world
from derived.test_stage3 import world3
from frozen.supplemental.test_boundaries import api


@pytest.fixture(autouse=True)
def bind(monkeypatch):
    monkeypatch.setattr(old, 'payload', payload)
    monkeypatch.setattr(old, 'seal', seal)
    monkeypatch.setattr(integrity, 'exported', exported)
    monkeypatch.setattr(integrity, 'seal', seal)
    monkeypatch.setattr(additional, 'payload', payload)
    monkeypatch.setattr(additional, 'seal', seal)


@pytest.mark.parametrize('corruption', ['receipt-party','receipt-start','receipt-end','receipt-body','receipt-move-order'],
                         ids=['D116-receipt-party','D116-receipt-start','D116-receipt-end','D116-receipt-body','D116-batch-order'])
def test_D116_checksum_valid_semantic_corruption_is_rejected(world, corruption, record_property):
    return old.test_D116_checksum_valid_semantic_corruption_is_rejected(world, corruption, record_property)


def test_B003_cross_owner_receipt_rejected(api, record_property):
    return old.test_B003_cross_owner_receipt_rejected(api, record_property)


def test_D333_atomic_operation_counter_sequence(world3, record_property):
    return integrity.test_D333_atomic_operation_counter_sequence(world3, record_property)


@pytest.mark.parametrize('mutation', integrity.CORRUPTIONS, ids=['D334-'+x for x in integrity.CORRUPTIONS])
def test_D334_checksum_valid_semantic_integrity(world3, mutation, record_property):
    return integrity.test_D334_checksum_valid_semantic_integrity(world3, mutation, record_property)


def test_D335_overlapping_original_dates_valid_roundtrip(world3, record_property):
    return integrity.test_D335_overlapping_original_dates_valid_roundtrip(world3, record_property)


@pytest.mark.parametrize('corruption',['plaintext-password','unknown-token-owner','duplicate-reservation-id',
    'overlapping-confirmed','inconsistent-instant','wrong-receipt-method','missing-receipt-body','invalid-zone'])
def test_D121_corrupt_semantic_state_rejects_without_replacement(world, corruption, record_property):
    return additional.test_D121_corrupt_semantic_state_rejects_without_replacement(world, corruption, record_property)
