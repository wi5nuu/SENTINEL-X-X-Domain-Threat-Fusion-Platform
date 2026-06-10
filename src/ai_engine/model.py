import torch
import torch.nn as nn
import math


class AirEncoder(nn.Module):
    def __init__(self, input_dim: int = 14, embedding_dim: int = 128):
        super().__init__()
        self.conv = nn.Conv1d(input_dim, embedding_dim, kernel_size=3, padding=1)
        self.attention = nn.MultiheadAttention(embedding_dim, num_heads=4, batch_first=True)
        self.norm = nn.LayerNorm(embedding_dim)

    def forward(self, x):
        x = x.transpose(1, 2)
        x = self.conv(x)
        x = x.transpose(1, 2)
        x, _ = self.attention(x, x, x)
        x = self.norm(x)
        return x.mean(dim=1)


class MaritimeEncoder(nn.Module):
    def __init__(self, input_dim: int = 12, embedding_dim: int = 128):
        super().__init__()
        self.conv = nn.Conv1d(input_dim, embedding_dim, kernel_size=3, padding=1)
        self.attention = nn.MultiheadAttention(embedding_dim, num_heads=4, batch_first=True)
        self.norm = nn.LayerNorm(embedding_dim)

    def forward(self, x):
        x = x.transpose(1, 2)
        x = self.conv(x)
        x = x.transpose(1, 2)
        x, _ = self.attention(x, x, x)
        x = self.norm(x)
        return x.mean(dim=1)


class SeismicEncoder(nn.Module):
    def __init__(self, input_dim: int = 5, embedding_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, embedding_dim),
        )

    def forward(self, x):
        return self.net(x)


class RFEncoder(nn.Module):
    def __init__(self, input_dim: int = 8, embedding_dim: int = 128):
        super().__init__()
        self.conv = nn.Conv1d(input_dim, embedding_dim, kernel_size=3, padding=1)
        self.pool = nn.AdaptiveAvgPool1d(1)

    def forward(self, x):
        x = x.transpose(1, 2)
        x = self.conv(x)
        x = self.pool(x)
        return x.squeeze(-1)


class CyberEncoder(nn.Module):
    def __init__(self, input_dim: int = 10, embedding_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, embedding_dim),
        )

    def forward(self, x):
        return self.net(x)


class SpaceEncoder(nn.Module):
    def __init__(self, input_dim: int = 12, embedding_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Linear(128, embedding_dim),
        )

    def forward(self, x):
        return self.net(x)


class TemporalTransformer(nn.Module):
    def __init__(self, embedding_dim: int = 128, num_heads: int = 4, num_layers: int = 4, max_seq_len: int = 256):
        super().__init__()
        self.pos_encoder = PositionalEncoding(embedding_dim, max_seq_len)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embedding_dim,
            nhead=num_heads,
            dim_feedforward=512,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

    def forward(self, x):
        x = self.pos_encoder(x)
        return self.transformer(x)


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int = 256):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, :x.size(1), :]


class ThreatFusionModel(nn.Module):
    def __init__(self, embedding_dim: int = 128, num_classes: int = 5):
        super().__init__()
        self.air_encoder = AirEncoder(embedding_dim=embedding_dim)
        self.maritime_encoder = MaritimeEncoder(embedding_dim=embedding_dim)
        self.seismic_encoder = SeismicEncoder(embedding_dim=embedding_dim)
        self.rf_encoder = RFEncoder(embedding_dim=embedding_dim)
        self.cyber_encoder = CyberEncoder(embedding_dim=embedding_dim)
        self.space_encoder = SpaceEncoder(embedding_dim=embedding_dim)

        self.temporal = TemporalTransformer(embedding_dim=embedding_dim)

        self.threat_classifier = nn.Sequential(
            nn.Linear(embedding_dim, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )
        self.compound_threat_head = nn.Sequential(
            nn.Linear(embedding_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 10),
        )
        self.eta_head = nn.Sequential(
            nn.Linear(embedding_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )
        self.confidence_head = nn.Sequential(
            nn.Linear(embedding_dim, 32),
            nn.ReLU(),
            nn.Sigmoid(),
            nn.Linear(32, 1),
        )

    def forward(self, air_x=None, maritime_x=None, seismic_x=None, rf_x=None, cyber_x=None, space_x=None):
        embeddings = []
        if air_x is not None:
            embeddings.append(self.air_encoder(air_x))
        if maritime_x is not None:
            embeddings.append(self.maritime_encoder(maritime_x))
        if seismic_x is not None:
            embeddings.append(self.seismic_encoder(seismic_x))
        if rf_x is not None:
            embeddings.append(self.rf_encoder(rf_x))
        if cyber_x is not None:
            embeddings.append(self.cyber_encoder(cyber_x))
        if space_x is not None:
            embeddings.append(self.space_encoder(space_x))

        if not embeddings:
            raise ValueError("At least one input stream required")

        fused = torch.stack(embeddings, dim=1)
        temporal_out = self.temporal(fused)
        pooled = temporal_out.mean(dim=1)

        return {
            "threat_class": self.threat_classifier(pooled),
            "compound_threat": self.compound_threat_head(pooled),
            "eta_minutes": self.eta_head(pooled),
            "confidence": self.confidence_head(pooled),
        }
