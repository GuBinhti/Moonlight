import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# Function to parse the lunar data file
def parse_lunar_data(file_path):
    """
    Parses the lunar data file to extract angle from full moon, illumination fraction, and lunar irradiance.

    :param file_path: Path to the file containing the lunar data.
    :return: A DataFrame containing the parsed data.
    """
    data = pd.read_csv(file_path, sep='|', skipinitialspace=True)


    data.columns = data.columns.str.strip()


    data['Angle from Full Moon (°)'] = data['Angle from Full Moon (°)'].astype(float)
    data['Scaled Lunar Irradiance (W/m²)'] = data['Scaled Lunar Irradiance (W/m²)'].astype(float)
    data['Illumination Fraction'] = data['Illumination Fraction'].apply(lambda x: float(x.strip('%')) / 100.0)

    return data



def normalize_to_maximum(y):
    """
    Normalizes irradiance values to a maximum of 1.

    :param y: List of irradiance values.
    :return: A list of normalized irradiance values.
    """
    max_irradiance = max(y)
    return [value / max_irradiance for value in y]



def normalize_data(data):
    """
    Normalize the illumination fraction and lunar irradiance.
    - Illumination Fraction remains the same.
    - Lunar Irradiance is normalized using the `normalize_to_maximum` function.

    :param data: DataFrame containing the lunar data.
    :return: Normalized DataFrame.
    """

    data['Normalized Illumination Fraction'] = data['Illumination Fraction']

    # Normalize the Lunar Irradiance using the provided function
    normalized_irradiance = normalize_to_maximum(data['Scaled Lunar Irradiance (W/m²)'])
    data['Normalized Lunar Irradiance'] = normalized_irradiance

    print("Phase Angle (°) | Normalized Irradiance")
    for angle, irradiance in zip(data['Angle from Full Moon (°)'], normalized_irradiance):
        print(f"{angle:.2f}°          | {irradiance:.6f}")

    return data



def plot_data(data):
    """
    Plots the normalized illumination fraction and lunar irradiance against the angle from full moon.
    Creates subplots, each holding 30 data points.

    :param data: DataFrame containing the normalized data.
    """

    normalized_data = normalize_data(data)

    num_points_per_subplot = 30
    num_subplots = int(np.ceil(len(normalized_data) / num_points_per_subplot))

    fig, axes = plt.subplots(num_subplots, 1, figsize=(10, 6 * num_subplots), sharex=True, sharey=True)

    if num_subplots == 1:
        axes = [axes]

    for i in range(num_subplots):
        start_index = i * num_points_per_subplot  # Start index for this subplot
        end_index = min((i + 1) * num_points_per_subplot, len(normalized_data))  # End index for this subplot

        # Slice the data for this subplot
        subplot_data = normalized_data.iloc[start_index:end_index]

        # Print the points being plotted
        for angle, illumination, irradiance in zip(subplot_data['Angle from Full Moon (°)'],
                                                   subplot_data['Normalized Illumination Fraction'],
                                                   subplot_data['Normalized Lunar Irradiance']):
            print(
                f"Angle: {angle:.2f}° | Illumination Fraction: {illumination:.5f} | Lunar Irradiance: {irradiance:.5f}")

        axes[i].scatter(subplot_data['Angle from Full Moon (°)'], subplot_data['Normalized Illumination Fraction'],
                        color="blue", label="Illumination Fraction", alpha=0.6)
        axes[i].scatter(subplot_data['Angle from Full Moon (°)'], subplot_data['Normalized Lunar Irradiance'],
                        color="red", label="Lunar Irradiance", alpha=0.6)

        axes[i].set_title(f"Moon Illumination Fraction & Irradiance vs Angle from Full Moon (Cycle {i + 1})")
        axes[i].set_xlabel("Angle from Full Moon (°)")
        axes[i].set_ylabel("Normalized Value")
        axes[i].grid(True)
        axes[i].legend()

    plt.tight_layout()

    plt.show()


# Main execution
file_path = '/Users/diegomateos/Downloads/lunar_irradiance_results.txt'  # Update with the correct path

# Parse the data
data = parse_lunar_data(file_path)

plot_data(data)
