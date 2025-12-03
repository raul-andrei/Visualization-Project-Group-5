import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

# Define the Autoencoder Network
class EconomyEncoder(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        # Encoder: Compresses 50+ metrics down to 2 dimensions
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 2)  # Latent Space (X, Y coordinates)
        )
        # Decoder: Tries to reconstruct the original data from 2 dimensions
        self.decoder = nn.Sequential(
            nn.Linear(2, 8),
            nn.ReLU(),
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, input_dim)
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return encoded, decoded

def get_neural_clusters(df):
    """
    Uses a PyTorch Autoencoder to generate the Visualization Coordinates
    instead of standard PCA.
    """
    # 1. Prepare Data (Numeric Only)
    features = ['Real_GDP_per_Capita_USD', 'Real_GDP_Growth_Rate_percent', 
                'Global_Risk', 'internet_users_total', 'roadways_km',
                'RE_Opp', 'Telecom_Opp', 'Logistics_Opp']
    
    # Clean and Standardize
    data = df[features].fillna(0).values
    scaler = StandardScaler()
    data_scaled = scaler.fit_transform(data)
    
    # Convert to PyTorch Tensor (CPU is faster for small data)
    tensor_data = torch.FloatTensor(data_scaled)
    
    # 2. Train the Brain
    input_dim = tensor_data.shape[1]
    model = EconomyEncoder(input_dim)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    
    # Fast Training Loop (500 Epochs)
    print("Training Neural Autoencoder...")
    for epoch in range(500):
        optimizer.zero_grad()
        encoded, decoded = model(tensor_data)
        loss = criterion(decoded, tensor_data)
        loss.backward()
        optimizer.step()
        
    # 3. Extract the "Thought Vector" (The 2D Coordinates)
    with torch.no_grad():
        encoded_data, _ = model(tensor_data)
        # Convert back to Numpy for Dash
        coordinates = encoded_data.numpy()
        
    return coordinates[:, 0], coordinates[:, 1]