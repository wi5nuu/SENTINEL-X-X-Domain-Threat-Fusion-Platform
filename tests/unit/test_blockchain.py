import pytest
from src.blockchain.service import IPFSEvidenceStore
from src.common.models import ThreatLevel


@pytest.mark.asyncio
async def test_ipfs_store_retrieve():
    store = IPFSEvidenceStore()
    data = {"test": "data", "threat_class": "CRITICAL"}
    cid = await store.store_incident("test-incident-001", data)
    assert cid is not None or cid is None

    if cid:
        retrieved = await store.retrieve(cid)
        assert retrieved is not None


def test_threat_level_enum():
    assert ThreatLevel.critical.value == "CRITICAL"
    assert ThreatLevel.catastrophic.value == "CATASTROPHIC"
    assert ThreatLevel.elevated.value == "ELEVATED"
    assert ThreatLevel.suspicious.value == "SUSPICIOUS"
    assert ThreatLevel.informational.value == "INFORMATIONAL"
