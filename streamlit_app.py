import streamlit as st
import folium
from streamlit_folium import folium_static
import geopandas as gpd
import rasterio
from rasterio.plot import show
from folium.raster_layers import ImageOverlay
import numpy as np
import os
import glob

try:
    from meteohub import run_meteohub
except ImportError:
    # st.error("The meteohub package is not installed. Please install it with `pip install meteohub`.")
    # install with `pip install meteohub` with subprocess
    import subprocess
    subprocess.run(["pip", "install", f"git+https://{st.secrets['GITHUB_TOKEN']}@github.com/SaferPlaces2023/meteohub.git"])



def read_geotiff(file_path):
    with rasterio.open(file_path) as src:
        bounds = src.bounds
        image = src.read(1)
        transform = src.transform
    return image, bounds, transform

def create_map(bounds):
    # Create a folium map centered on the bounds
    m = folium.Map(location=[(bounds.bottom + bounds.top) / 2, (bounds.left + bounds.right) / 2], zoom_start=7)
    return m

def add_geotiff_to_map(m, image, bounds, transform):
    # Normalize the image
    img_array = np.array(image)
    img_array = (img_array - img_array.min()) / (img_array.max() - img_array.min())
    img_array = (img_array * 255).astype(np.uint8)
    
    # Create an ImageOverlay from the image and add it to the map
    folium.raster_layers.ImageOverlay(
        image=img_array,
        bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
        opacity=0.7,
        interactive=True,
        cross_origin=False,
        zindex=1,
    ).add_to(m)

def remove_tif_files():
    # Remove all .tif files in the current directory
    tif_files = glob.glob("*.tif")
    for tif_file in tif_files:
        os.remove(tif_file)
        
# Streamlit app
st.title("GeoTIFF Layers Viewer")

# Inputs for meteohub request
dataset = st.text_input(label="Dataset", value="COSMO-2I", help="The dataset to download.")
varname = st.text_input(label="Varname", value="tp", help="The variable name to extract from the grib file.")
bbox = st.text_input(label="Bbox", value="11.9,45,13.2,46", help="The bounding box to extract the data.")
date = st.text_input(label="Date", value="", help="The datetime to download with format %Y-%m-%d. Default is latest datetime available.")
run = st.text_input(label="Run", value="00:00", help="The dataset to download.")
start_fc = st.text_input(label="Start Forecast", value="1", help="The hour at which the accumulation starts.")
end_fc = st.text_input(label="End Forecast", value=None, help="The hour at which the accumulation ends.")
fc_range = st.checkbox(label="Forecast Range", help="If True the output will be multiple tif files, one for each forecast hour. Default is False")
out = f"{dataset}_{varname}_{date}_{run}_{start_fc}-{end_fc}.tif"

# Button to run meteohub request
if st.button("Run meteohub_request"):
    # Remove all .tif files before running the command
    remove_tif_files()
    result = run_meteohub(dataset=dataset,
                          varname=varname,
                          bbox=bbox,
                          date=date,
                          run=run,
                          out=out,
                          start_fc=start_fc,
                          end_fc=end_fc,
                          fc_range=fc_range,
                          debug=True)
    st.success(result)

# Find GeoTIFF files generated by meteohub request
files = os.listdir()
gtiff_files = [file for file in files if file.startswith(out.split(".tif")[0])]

# Read GeoTIFF data
gtiff_data = []
for gtif in gtiff_files:
    image, bounds, transform = read_geotiff(gtif)
    gtiff_data.append((image, bounds, transform))

# Check if there are any GeoTIFF files
if gtiff_data:
    # Create a folium map
    bounds = gtiff_data[0][1]
    m = create_map(bounds)

    # Create a slider to select the layer
    layer = st.slider("Select Layer", 1, len(gtiff_data), 1)

    # Add the selected layer to the map
    selected_data = gtiff_data[layer - 1]
    add_geotiff_to_map(m, selected_data[0], selected_data[1], selected_data[2])

    # Display the map in Streamlit
    folium_static(m)
else:
    st.warning("No GeoTIFF files found.")
