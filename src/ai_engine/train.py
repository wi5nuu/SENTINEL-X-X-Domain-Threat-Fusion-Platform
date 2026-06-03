import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, random_split
import numpy as np
import os
from datetime import datetime

from src.common.logging import setup_logging
from src.ai_engine.model import ThreatFusionModel

logger = setup_logging("ai-trainer")

NUM_CLASSES = 5
EMBEDDING_DIM = 128
BATCH_SIZE = 64
EPOCHS = 20
LEARNING_RATE = 1e-3
MODEL_PATH = os.environ.get("MODEL_PATH", "models/threat_fusion_v1.pt")
SEQUENCE_LEN = 64


def generate_realistic_dataset(num_samples: int = 10000):
    air = torch.zeros(num_samples, SEQUENCE_LEN, 14)
    maritime = torch.zeros(num_samples, SEQUENCE_LEN, 12)
    seismic = torch.zeros(num_samples, SEQUENCE_LEN, 5)
    rf = torch.zeros(num_samples, SEQUENCE_LEN, 8)
    cyber = torch.zeros(num_samples, SEQUENCE_LEN, 10)
    threat_labels = torch.zeros(num_samples, dtype=torch.long)
    compound_labels = torch.zeros(num_samples, 10)
    eta_targets = torch.zeros(num_samples, 1)
    confidence_targets = torch.zeros(num_samples, 1)

    for i in range(num_samples):
        threat_level = np.random.choice(5, p=[0.50, 0.25, 0.12, 0.08, 0.05])
        threat_labels[i] = threat_level

        is_anomalous = threat_level >= 1
        is_escalated = threat_level >= 2
        is_critical = threat_level >= 3
        is_catastrophic = threat_level >= 4

        for t in range(SEQUENCE_LEN):
            air[i, t] = torch.tensor([
                np.random.uniform(-90, 90),
                np.random.uniform(-180, 180),
                np.random.uniform(0, 12000),
                np.random.uniform(0, 12000),
                np.random.uniform(0, 280),
                np.random.uniform(0, 360),
                np.random.uniform(-20, 20),
                np.random.uniform(0, 1),
                np.random.uniform(0, 1),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
            ])
            maritime[i, t] = torch.tensor([
                np.random.uniform(-90, 90),
                np.random.uniform(-180, 180),
                np.random.uniform(0, 30),
                np.random.uniform(0, 360),
                np.random.uniform(0, 360),
                float(np.random.choice(range(6))),
                float(np.random.choice(range(7))),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
                float(np.random.uniform(0, 1)),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
            ])
            seismic[i, t] = torch.tensor([
                np.random.uniform(-90, 90),
                np.random.uniform(-180, 180),
                np.random.uniform(0, 100),
                np.random.exponential(1.5) if is_anomalous else np.random.uniform(0, 3),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
            ])
            rf[i, t] = torch.tensor([
                np.random.choice([433, 915, 2400, 5800, 1575]),
                np.random.uniform(100, 20000),
                np.random.uniform(-120, -30),
                np.random.uniform(-90, 90),
                np.random.uniform(-180, 180),
                np.random.uniform(0, 1),
                float(np.random.choice([0, 1, 2, 3], p=[0.85, 0.08, 0.05, 0.02])),
                float(np.random.choice([0, 1], p=[0.95, 0.05])),
            ])
            cyber[i, t] = torch.tensor([
                np.random.uniform(0, 1),
                float(np.random.randint(0, 65535)),
                float(np.random.choice([80, 443, 22, 3389, 502, 102, 20000, 44818])),
                float(np.random.choice([6, 17])),
                float(np.random.choice(range(12))),
                float(np.random.choice(range(6))),
                float(threat_level),
                np.random.uniform(0, 1),
                float(np.random.choice([0, 1], p=[0.9, 0.1])),
                float(np.random.choice([0, 1], p=[0.9, 0.1])),
            ])

        if is_anomalous:
            for t in range(SEQUENCE_LEN):
                anomaly_strength = np.random.uniform(0.1, 1.0) if is_catastrophic else np.random.uniform(0.1, 0.5)
                if threat_level == 1:
                    rf[i, t, 6] = np.random.choice([1, 2])
                elif threat_level >= 2:
                    air[i, t, 11] = 1.0
                    maritime[i, t, 10] = 1.0
                    cyber[i, t, 6] = float(threat_level)
                    seismic[i, t, 3] = np.random.exponential(threat_level)
                    rf[i, t, 6] = float(np.random.choice([2, 3], p=[0.7, 0.3]))
                    if is_critical:
                        cyber[i, t, 8] = 1.0
                        rf[i, t, 7] = 1.0
                        maritime[i, t, 9] = 1.0
                    if is_catastrophic:
                        air[i, t, 12] = 1.0
                        air[i, t, 13] = 1.0
                        cyber[i, t, 9] = 1.0

        sample_compound = [0] * 10
        if is_anomalous:
            if threat_level >= 1:
                sample_compound[0] = 1
                sample_compound[1] = 1
            if threat_level >= 2:
                sample_compound[2] = 1
                sample_compound[3] = 1
            if threat_level >= 3:
                sample_compound[4] = 1
                sample_compound[5] = 1
                sample_compound[6] = 1
            if threat_level >= 4:
                sample_compound[7] = 1
                sample_compound[8] = 1
                sample_compound[9] = 1
        compound_labels[i] = torch.tensor(sample_compound)

        if is_anomalous:
            eta_targets[i] = torch.tensor([[np.random.uniform(5, 60) if threat_level >= 2 else np.random.uniform(30, 120)]])
        else:
            eta_targets[i] = torch.tensor([[np.random.uniform(60, 240)]])
        confidence_targets[i] = torch.tensor([[min(1.0, threat_level / 5.0 + np.random.uniform(-0.1, 0.1))]])

    logger.info(f"Generated {num_samples} samples: "
                f"class distribution={np.bincount(threat_labels.numpy(), minlength=5).tolist()}")
    return air, maritime, seismic, rf, cyber, threat_labels, compound_labels, eta_targets, confidence_targets


def train():
    os.makedirs(os.path.dirname(MODEL_PATH) or ".", exist_ok=True)
    logger.info("Starting enhanced model training")

    model = ThreatFusionModel(embedding_dim=EMBEDDING_DIM, num_classes=NUM_CLASSES)

    data = generate_realistic_dataset(50000)
    dataset = TensorDataset(*data)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_ds, val_ds = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)

    class_weights = torch.tensor([0.5, 1.0, 2.0, 4.0, 6.0])
    ce_criterion = nn.CrossEntropyLoss(weight=class_weights)
    bce_criterion = nn.BCEWithLogitsLoss()
    mse_criterion = nn.MSELoss()

    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val_loss = float("inf")
    for epoch in range(EPOCHS):
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        for batch in train_loader:
            air_b, mar_b, seis_b, rf_b, cyb_b, lab_b, comp_b, eta_b, conf_b = batch
            optimizer.zero_grad()
            outputs = model(air_x=air_b, maritime_x=mar_b, seismic_x=seis_b, rf_x=rf_b, cyber_x=cyb_b)

            loss_cls = ce_criterion(outputs["threat_class"], lab_b)
            loss_compound = bce_criterion(outputs["compound_threat"], comp_b)
            loss_eta = mse_criterion(outputs["eta_minutes"].squeeze(), eta_b.squeeze())
            loss_conf = mse_criterion(outputs["confidence"].squeeze(), conf_b.squeeze())

            loss = loss_cls + loss_compound + loss_eta + loss_conf
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            train_loss += loss.item()
            preds = outputs["threat_class"].argmax(dim=1)
            train_correct += (preds == lab_b).sum().item()
            train_total += lab_b.size(0)

        scheduler.step()

        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for batch in val_loader:
                air_b, mar_b, seis_b, rf_b, cyb_b, lab_b, comp_b, eta_b, conf_b = batch
                outputs = model(air_x=air_b, maritime_x=mar_b, seismic_x=seis_b, rf_x=rf_b, cyber_x=cyb_b)

                loss_cls = ce_criterion(outputs["threat_class"], lab_b)
                loss_compound = bce_criterion(outputs["compound_threat"], comp_b)
                loss_eta = mse_criterion(outputs["eta_minutes"].squeeze(), eta_b.squeeze())
                loss_conf = mse_criterion(outputs["confidence"].squeeze(), conf_b.squeeze())

                val_loss += (loss_cls + loss_compound + loss_eta + loss_conf).item()
                preds = outputs["threat_class"].argmax(dim=1)
                val_correct += (preds == lab_b).sum().item()
                val_total += lab_b.size(0)

        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        train_acc = train_correct / train_total * 100
        val_acc = val_correct / val_total * 100

        logger.info(
            f"Epoch {epoch+1}/{EPOCHS} | "
            f"Train Loss: {avg_train_loss:.4f} Acc: {train_acc:.2f}% | "
            f"Val Loss: {avg_val_loss:.4f} Acc: {val_acc:.2f}%"
        )

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(model.state_dict(), MODEL_PATH)
            logger.info(f"New best model saved to {MODEL_PATH} (val_loss: {avg_val_loss:.4f})")

    logger.info(f"Training complete. Best model: {MODEL_PATH}")
    return model


if __name__ == "__main__":
    train()
