import requests
import statistics
from datetime import datetime
from functools import lru_cache
import numpy as np
current_time = datetime.utcnow()
day_track = str(current_time.day).zfill(2)  # Optimized to use current_time.day directly
@lru_cache(maxsize=32)
def load_data(url):
    response = requests.get(url)
    return response.text.splitlines()
# Function to load the 27-day space weather outlook data
def kp_solar(url):
    data = load_data(url)
    
    for line in data:
        if line.startswith("#") or not line.strip():  # Skip header or empty lines
            continue
        parts = line.split()
        if parts[2] == day_track:
            solar_index = int(parts[3])
            kp_vall = int(parts[-1])
            return kp_vall, solar_index
    return None, None
def geteflux(url):
    data = load_data(url)
    
    for i, line in enumerate(data):
        if "GOES Electron Flux" in line:
            flux_line = data[i + 3].strip()
            parts = flux_line.split()
            if len(parts) >= 5:
                try:
                    return float(parts[3])  # GOES Electron Flux >2 MeV
                except ValueError:
                    return None  # Return None if conversion fails
    return None
def gw_to_rayleighs(wavelength_nm, power_gw_list, efficiency=0.01):
    """
    Convert a list of hemispheric power values (in gigawatts) and wavelength (in nanometers) to Rayleighs.
    
    :param wavelength_nm: Wavelength of the aurora in nanometers
    :param power_gw_list: List of hemispheric power values in gigawatts
    :param efficiency: Efficiency of converting power to light (default is 1%)
    :return: List of equivalent brightness values in Rayleighs
    """
    h = 6.626e-34  # Planck's constant in Joules * seconds
    c = 3e8  # Speed of light in meters/second
    wavelength_m = wavelength_nm * 1e-9  # Convert wavelength from nanometers to meters
    photon_energy_j = (h * c) / (wavelength_m+1)  # Energy of one photon
    
    # Convert power from gigawatts to watts and calculate Rayleighs for each power value
    return [(power_gw * 1e9 * efficiency / (photon_energy_j+1)) / 1e6 for power_gw in power_gw_list]
def calculate_variance(differences):
    return np.var(differences)
def find_path_of_most_variance(aurora_intensity_cache):
    rows = len(aurora_intensity_cache)
    cols = len(aurora_intensity_cache[0])
    best_path = []
    max_variance = -1
    for start_row in range(rows):
        path = [(start_row, cols - 1)]
        differences = []
        current_row, current_col = start_row, cols - 1
        while current_col > 0:
            # Get the neighboring cells (left, top-left, bottom-left)
            neighbors = []
            if current_col > 0:
                neighbors.append((current_row, current_col - 1))
            if current_row > 0:
                neighbors.append((current_row - 1, current_col - 1))
            if current_row < rows - 1:
                neighbors.append((current_row + 1, current_col - 1))
            # Find the neighbor with the maximum absolute difference in intensity
            max_diff = -1
            next_cell = None
            for neighbor in neighbors:
                neighbor_row = neighbor[0]
                neighbor_col = neighbor[1]
                diff = abs(aurora_intensity_cache[current_row][current_col] - aurora_intensity_cache[neighbor_row][neighbor_col])
                if diff > max_diff:
                    max_diff = diff
                    next_cell = neighbor
            # Move to the next cell
            if next_cell:
                path.append(next_cell)
                differences.append(max_diff)
                current_row = next_cell[0]
                current_col = next_cell[1]
            # Calculate the variance of the differences for the current path
            if differences:
                variance = calculate_variance(np.array(differences))
                if variance > max_variance:
                    max_variance = variance
                    best_path = path

    return best_path, max_variance

 