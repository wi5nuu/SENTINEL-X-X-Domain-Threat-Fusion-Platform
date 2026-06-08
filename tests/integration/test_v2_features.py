import pytest
from src.ai_engine.model import ThreatFusionModel
import torch

def test_space_encoder_integration():
    """Test that the SpaceEncoder is correctly integrated into the Fusion Model"""
    model = ThreatFusionModel(embedding_dim=128)
    
    # Create dummy inputs for all 6 domains
    air_x = torch.randn(1, 10, 14)
    mar_x = torch.randn(1, 10, 12)
    sei_x = torch.randn(1, 5)
    rf_x = torch.randn(1, 10, 8)
    cyb_x = torch.randn(1, 10)
    spa_x = torch.randn(1, 6)
    
    output = model(
        air_x=air_x,
        maritime_x=mar_x,
        seismic_x=sei_x,
        rf_x=rf_x,
        cyber_x=cyb_x,
        space_x=spa_x
    )
    
    assert "threat_class" in output
    assert "confidence" in output
    assert output["threat_class"].shape == (1, 5)
    print("SpaceEncoder integration test passed!")

def test_xai_reasoning():
    """Test the XAI reasoning logic in SentinelAnalyst"""
    from src.ai_engine.analyst import SentinelAnalyst
    from src.common.models import Alert, ThreatLevel
    from datetime import datetime
    
    analyst = SentinelAnalyst()
    alert = Alert(
        id="test-alert",
        timestamp_utc=datetime.utcnow(),
        threat_class=ThreatLevel.critical,
        confidence=0.95,
        domain="air",
        description="Emergency squawk 7700 detected"
    )
    
    reason = analyst._generate_xai_reason(alert)
    assert "Emergency squawk detected" in reason
    assert "High-confidence ADS-B signature match" in reason
    print("XAI reasoning test passed!")
