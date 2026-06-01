import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from datetime import datetime

from src.common.logging import setup_logging
from src.ai_engine.model import ThreatFusionModel

logger = setup_logging("ai-trainer")

NUM_CLASSES = 5
EMBEDDING_DIM = 128
BATCH_SIZE = 64
EPOCHS = 10
LEARNING_RATE = 1e-3


def generate_synthetic_dataset(num_samples: int = 10000):
    air = torch.randn(num_samples, 64, 14)
    maritime = torch.randn(num_samples, 64, 12)
    seismic = torch.randn(num_samples, 64, 5)
    rf = torch.randn(num_samples, 64, 8)
    cyber = torch.randn(num_samples, 64, 10)
    labels = torch.randint(0, 5, (num_samples,))
    return air, maritime, seismic, rf, cyber, labels


def train():
    logger.info("Starting model training")
    model = ThreatFusionModel(embedding_dim=EMBEDDING_DIM, num_classes=NUM_CLASSES)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

    air, maritime, seismic, rf, cyber, labels = generate_synthetic_dataset(50000)
    dataset = TensorDataset(air, maritime, seismic, rf, cyber, labels)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0
        for batch in loader:
            air_b, mar_b, seis_b, rf_b, cyb_b, lab_b = batch
            optimizer.zero_grad()
            outputs = model(air_x=air_b, maritime_x=mar_b, seismic_x=seis_b, rf_x=rf_b, cyber_x=cyb_b)
            loss = criterion(outputs["threat_class"], lab_b)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        avg_loss = total_loss / len(loader)
        logger.info(f"Epoch {epoch+1}/{EPOCHS}, Loss: {avg_loss:.4f}")

    torch.save(model.state_dict(), "/models/threat_fusion_v1.pt")
    logger.info("Model saved to /models/threat_fusion_v1.pt")
    return model


if __name__ == "__main__":
    train()
