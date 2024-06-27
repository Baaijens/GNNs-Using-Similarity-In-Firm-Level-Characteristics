# -*- coding: utf-8 -*-
"""Edge Creation Based On Charecteristic Similarity .ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1qegXCZSBMuocV0IgPZ4yRb9QcpGpCw_3

Set up OS
"""

!pip install google-auth google-auth-oauthlib google-auth-httplib2
!pip install google-api-python-client
from google.colab import auth
auth.authenticate_user()

from google.colab import drive
drive.mount('/content/drive')
import pandas as pd
import os
os.chdir('/content/drive/My Drive')

"""# Load Panel Data"""

df = pd.read_csv("/content/drive/MyDrive/Min_Charecteristics_Tilburg_1963_ALLSAMPLE.csv")

"""# Imports"""

!pip install torch_geometric
import pandas as pd
import numpy as np
import torch
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
from torch_geometric.data import Data
from scipy.spatial.distance import cdist

"""# Normalize data And lag feutures"""

df['Mom1m'] = df['excess_return']
df['Y_excess_return'] = df['excess_return']
# Remove duplicates while keeping the last occurrence
df = df.sort_values('date').drop_duplicates(subset=['date', 'PERMNO'], keep='last')




df = df.sort_values(by=['PERMNO', 'date'])
# Shift the excess return by one month within each firm

# List of column names to lag
factor_columns = [
    "Beta", "RoE", "InvestPPEInv", "ShareIss5Y", "Accruals", "dNoa",
    "GP", "AssetGrowth",  "Investment", "market_cap_adjusted", "excess_return",
    "BM", "CompEquIss", "OperProf",  "MaxRet", "IndMom", "DolVol" ,"Mom1m" , "Mom6m", "Mom12m"
]


# Loop through each column in the list and shift them forward by one period within each group
for column in factor_columns:
    df[column] = df.groupby('PERMNO')[column].shift(1)




# List of column names to standardize
factor_columns = [
    "Beta", "RoE", "InvestPPEInv", "ShareIss5Y", "Accruals", "dNoa",
    "GP", "AssetGrowth",  "Investment", "market_cap_adjusted",
    "BM", "CompEquIss", "OperProf",  "MaxRet", "IndMom", "DolVol" ,"Mom1m" , "Mom6m", "Mom12m"
]
# Compute the mean and standard deviation for each factor column grouped by 'date'
means = df.groupby('date')[factor_columns].transform('mean')
stds = df.groupby('date')[factor_columns].transform('std')

# Standardize the existing columns without creating new ones
for column in factor_columns:
    df[column] = (df[column] - means[column]) / stds[column]


df = df.dropna()

"""# Convert panel data to graph data for each month

# Using Euclidean Distance

Function construct_graph_with_absolute_correlation to construct the graphs based on pairwise simularity between firm and their characteristics, based on Euclidean distance.
"""

import os
import pandas as pd
import numpy as np
import torch
from torch_geometric.data import Data

def construct_graph_with_absolute_correlation(df, factor_columns, return_column, W, theta):
    # Store the original date format
    original_dates = pd.to_datetime(df['date'])

    # Dynamic directory name based on W and theta
    save_dir = f'Corrsaved(absolute)_graphs_W{W}_theta{theta}'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Convert 'date' column to integer format
    df['formatted_date'] = original_dates.dt.strftime('%Y%m%d').astype(int)
    unique_dates = sorted(df['formatted_date'].unique())

    # Loop over each date starting from the Wth date to ensure a full window
    for i in range(W - 1, len(unique_dates)):
        current_date = unique_dates[i]
        window_dates = unique_dates[i - W + 1:i + 1]
        window_df = df[df['formatted_date'].isin(window_dates)]

        # Skip this iteration if required columns are missing
        if 'PERMNO' not in window_df.columns or return_column not in window_df.columns:
            continue

        # Create pivot table for the return column
        pivot_df = window_df.pivot(index='formatted_date', columns='PERMNO', values=return_column)
        correlation_matrix = pivot_df.corr().values

        # Get absolute values of the correlation matrix
        abs_corr = np.abs(correlation_matrix)
        edge_indices = np.where((abs_corr > theta) & (np.eye(len(df['PERMNO'].unique()), dtype=bool) == False))

        # Convert edge indices and weights to tensors
        edge_index = torch.tensor(np.array(edge_indices), dtype=torch.long)
        edge_weights = torch.tensor(abs_corr[edge_indices], dtype=torch.float)

        # Get the latest data for the current date
        latest_df = df[df['formatted_date'] == current_date]
        if 'PERMNO' in latest_df.columns:
            # Prepare node features tensor
            latest_attributes = latest_df[['PERMNO'] + factor_columns].set_index('PERMNO').reindex(df['PERMNO'].unique())
            node_features_tensor = torch.tensor(latest_attributes.drop(columns='PERMNO', errors='ignore').values, dtype=torch.float)
            permno_tensor = torch.tensor(latest_attributes.index.values, dtype=torch.int)

            # Ensure 'date' is also saved as a tensor
            date_tensor = torch.tensor([current_date] * len(latest_attributes), dtype=torch.long)

            # Create graph data object
            graph_data = Data(x=node_features_tensor, edge_index=edge_index, edge_attr=edge_weights, permno=permno_tensor, date=date_tensor)
            filename = f"CorrGraph_{current_date}_W{W}_theta{theta}.pt"
            filepath = os.path.join(save_dir, filename)
            torch.save(graph_data, filepath)
            print(f"Graph for {current_date} saved to {filepath}")
            print(f"Graph for {current_date}: {len(df['PERMNO'].unique())} nodes, {edge_index.size(1) // 2} edges")
        else:
            print(f"Missing 'PERMNO' in latest data for {current_date}")

    # Cleanup to avoid confusion
    df.drop('formatted_date', axis=1, inplace=True)


# Define the return column
return_column = "excess_return"

"""Call the Function"""

factor_columns = [
    "Beta", "RoE", "InvestPPEInv", "ShareIss5Y", "Accruals", "dNoa",
    "GP", "AssetGrowth",  "Investment", "market_cap_adjusted",
    "BM", "CompEquIss", "OperProf",  "MaxRet", "IndMom", "DolVol" ,"Mom1m" , "Mom6m", "Mom12m", "Y_excess_return"]
factor_columns_for_similarity = [col for col in factor_columns if col != 'Y_excess_return']
W = 24  # Window size
sigmas = [4,9]  # Example sigma values
thetas = [0.00001, 0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.9]  # Example theta values

optimized_construct_graph_aligned_pytorch(df, factor_columns, factor_columns_for_similarity, W, sigmas, thetas)

"""# Using Cosine Simularity

Function for cosine simularity is defined here: construct_graph_cosine_similarity
"""

def construct_graph_cosine_similarity(df_original, factor_columns, factor_columns_for_similarity, W_values, percentile_thresholds):
    # Loop over different window sizes (W) and percentile thresholds
    for W in W_values:
        for percentile_threshold in percentile_thresholds:
            # Convert 'date' column to datetime format and create a save directory
            original_dates = pd.to_datetime(df_original['date'])
            save_dir = f"Pair-cosine(1963)_Min_FILTERED_W{W}_Percentile{percentile_threshold}"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            df = df_original.copy()  # Use a copy to preserve the original df
            df['date'] = original_dates.dt.strftime('%Y%m%d').astype(int)  # Convert dates to integer format
            unique_dates = sorted(df['date'].unique())  # Get unique dates

            all_edge_weights = []  # Collect all edge weights for histogram

            # Iterate over each date in the window
            for i in range(W - 1, len(unique_dates)):
                current_date = unique_dates[i]
                current_firms = df[df['date'] == current_date]

                # Define the date window and filter the DataFrame
                window_dates = unique_dates[i - W + 1:i + 1]
                window_df = df[df['date'].isin(window_dates) & df['PERMNO'].isin(current_firms['PERMNO'])]

                if not window_df.empty:
                    unique_permnos = current_firms['PERMNO'].unique()
                    permno_to_index = {permno: idx for idx, permno in enumerate(unique_permnos)}

                    edge_index = []
                    edge_weights = []

                    cosine_similarity_sum = np.zeros((len(unique_permnos), len(unique_permnos)))

                    # Calculate cosine similarity for each date in the window
                    for window_date in window_dates:
                        date_df = window_df[window_df['date'] == window_date]
                        if not date_df.empty:
                            feature_values = date_df[factor_columns_for_similarity].values
                            norms = np.linalg.norm(feature_values, axis=1)
                            normalized_features = feature_values / norms[:, np.newaxis]
                            cosine_similarity = np.dot(normalized_features, normalized_features.T)
                            np.fill_diagonal(cosine_similarity, 0)  # Remove self-loops

                            # Sum the cosine similarities over the window
                            for i, permno_i in enumerate(date_df['PERMNO'].values):
                                for j, permno_j in enumerate(date_df['PERMNO'].values):
                                    if i < j:
                                        index_i = permno_to_index[permno_i]
                                        index_j = permno_to_index[permno_j]
                                        cosine_similarity_sum[index_i, index_j] += cosine_similarity[i, j]
                                        cosine_similarity_sum[index_j, index_i] += cosine_similarity[i, j]

                    # Average cosine similarity over the window
                    avg_cosine_similarity = cosine_similarity_sum / W
                    all_edge_weights.extend(avg_cosine_similarity.flatten())

                    # Calculate dynamic threshold based on absolute values farthest from zero
                    dynamic_theta = np.percentile(np.abs(avg_cosine_similarity), 100 - percentile_threshold)

                    # Create edges based on the threshold
                    for i in range(len(unique_permnos)):
                        for j in range(i + 1, len(unique_permnos)):
                            weight = avg_cosine_similarity[i, j]
                            if np.abs(weight) > dynamic_theta:
                                edge_index.append([i, j])
                                edge_index.append([j, i])
                                edge_weights.extend([weight, weight])

                    # Convert edges and weights to tensors
                    edge_index_tensor = torch.tensor(edge_index, dtype=torch.long).t().contiguous()
                    edge_attr_tensor = torch.tensor(edge_weights, dtype=torch.float)
                    latest_attributes = window_df[window_df['date'] == current_date].groupby('PERMNO').last()[factor_columns]
                    node_features_tensor = torch.tensor(latest_attributes.values, dtype=torch.float)

                    # Create graph data object
                    graph_data = Data(x=node_features_tensor, edge_index=edge_index_tensor, edge_attr=edge_attr_tensor)
                    graph_data.permno = torch.tensor(latest_attributes.index.tolist(), dtype=torch.long)
                    graph_data.date = torch.tensor([current_date] * len(latest_attributes), dtype=torch.long)

                    # Save the graph data to a file
                    filename = f"Pair-cosine(1963)_Min_FILTERED_{current_date}_W{W}_Percentile{percentile_threshold}_Abs.pt"
                    filepath = os.path.join(save_dir, filename)
                    torch.save(graph_data, filepath)
                    print(f"Graph for {current_date}: {graph_data.num_nodes} nodes, {graph_data.num_edges // 2} edges saved to {filepath}")

            # Plot and save histogram of all edge weights
            mpl.style.use('seaborn-whitegrid')
            plt.rcParams['font.family'] = 'Arial'
            plt.rcParams['font.size'] = 12

            plt.figure(figsize=(8, 5))
            plt.hist(all_edge_weights, bins=50, color='grey', alpha=0.6)

            plt.title(f'Distribution of Absolute Edge Weights for W={W} and Percentile={percentile_threshold}', fontsize=14, fontweight='bold')
            plt.xlabel('Absolute Edge Weight', fontsize=12)
            plt.ylabel('Frequency', fontsize=12)

            plt.grid(True, linestyle='--', linewidth=0.5, color='gray', alpha=0.5)
            plt.tight_layout()
            plt.show()

"""Call the Function specifying the rolling window size (W), and the Percentile tresholds."""

factor_columns = [
    "Beta", "RoE", "InvestPPEInv", "ShareIss5Y", "Accruals", "dNoa",
    "GP", "AssetGrowth", "Investment", "market_cap_adjusted",
    "BM", "CompEquIss", "OperProf", "MaxRet", "IndMom", "DolVol", "Mom1m", "Mom6m", "Mom12m", "Y_excess_return"]
factor_columns_for_similarity = [col for col in factor_columns if col != 'Y_excess_return']
W_values = [12, 24, 36, 48, 60]  # Different window sizes to iterate over
percentile_thresholds = [10, 20, 30, 40, 50, 60, 80, 90, 100]  # Different percentile thresholds to iterate over

construct_graph_cosine_similarity(df, factor_columns, factor_columns_for_similarity, W_values, percentile_thresholds)