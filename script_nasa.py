import pandas as pd
import geopandas as gpd
from sklearn.cluster import DBSCAN
from shapely.ops import unary_union
import os
from shapely.geometry import Point, box
import requests
import io
import zipfile
from tqdm import tqdm
import json
import tempfile
from datetime import datetime
import numpy as np

def squarify(instrument, point):
    """
    Création d'un carré autour du point en fonction de l'instrument.
    """
    if instrument == "VIIRS":
        return box(
            point.x - 187.5, point.y - 187.5, point.x + 187.5, point.y + 187.5
        )
    if instrument == "MODIS":
        return box(
            point.x - 500, point.y - 500, point.x + 500, point.y + 500
        )


### RECUPERATION DES DONNÉES EN TEMPS RÉEL
DEBUT_FEU = "2026-07-22"
SUD_OUEST = "-1.3912771298258413,44.26260201941759,-0.8286147086117207,44.95664839180941"
# INCENDIES = [{"name": "Biscarosse", "bbox": "-1.2330681357418947,44.18977389277515,-0.9415839178186362,44.42266633001196", "date_debut":"2026-07-23"}, {"name": "Lège-Cap-Ferret", "bbox": "-1.3265224975898737,44.612994554486995,-0.9733807611689691,44.93782558410414", "date_debut":"2026-07-22"}]
df_feu = pd.DataFrame()

satellites = ["VIIRS_NOAA20_NRT","MODIS_NRT","VIIRS_NOAA21_NRT","VIIRS_SNPP_NRT"]
NASA_API_KEY = os.environ["NASA_FIRMS_API_KEY"]
url = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{}/{}/{}/1/{}"

for date in pd.date_range(start=DEBUT_FEU, end=datetime.now().date()):
    for satellite in satellites:
        response = requests.get(url.format(NASA_API_KEY, satellite, SUD_OUEST, date.strftime("%Y-%m-%d")))
        try:
            response.raise_for_status()
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text))
                if df.empty:
                    print(f"No data for {satellite} on {date.strftime('%Y-%m-%d')}")
                    continue
                df['date_end'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df['date_complete'] = pd.to_datetime(df['acq_date'] + ' ' + df['acq_time'].astype(str).str.zfill(4), format="%Y-%m-%d %H%M")
                df['date_complete'] = df['date_complete'] + pd.Timedelta(hours=2)  # Correction du décalage horaire
                df_feu = pd.concat([df_feu, df])
                
            else:
                print(f"Failed to download data for {satellite} on {date.strftime('%Y-%m-%d')}: Status code {response.status_code}")
        except requests.RequestException as e:
            print(f"Failed to download data for {satellite}: {e}")

df_feu.reset_index(drop=True, inplace=True)
file_path = 'data/output/feux NASA/feux_sud_ouest.csv'
os.makedirs(os.path.dirname(file_path), exist_ok=True)
df_feu.to_csv(file_path, index=False)
print(f"Data saved to {file_path}")
# gdf_feu_active = gpd.GeoDataFrame(df_feu, geometry=gpd.points_from_xy(df_feu['longitude'], df_feu['latitude']))
# gdf_feu_active.set_crs(epsg=4326, inplace=True) 
# gdf_feu_active = gdf_feu_active.to_crs(epsg=2154) 

### CRÉATION DES CARRÉS AUTOUR DES POINTS D'INCENDIE

# gdf_feu_active['square'] = gdf_feu_active.apply(lambda row: squarify(row['instrument'], row.geometry), axis=1)

# gdf_feu_active = gdf_feu_active.drop(columns='geometry')
# gdf_feu_active.geometry = gdf_feu_active['square']
# gdf_feu_active.set_crs(epsg=2154, inplace=True)

# # gdf_feu_active['type'] = gdf_feu_active['acq_date'].apply(
# #     lambda x: 0 if (datetime(2025, 7, 18) - pd.to_datetime(x)) <= pd.Timedelta(days=1) else 1 # CHANGER datetime(2025, 7, 18) EN datetime.now().date() EN PROD !!!
# # )

# gdf_feu_active.to_crs(epsg=4326, inplace=True) # CHANGER LA PROJECTION EN FONCTION DES BESOINS ICI !
# gdf_feu_active.to_file('data/output/feux_jour.geojson', driver='GeoJSON')