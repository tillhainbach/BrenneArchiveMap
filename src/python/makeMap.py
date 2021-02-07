import folium
from folium.plugins import MarkerCluster
import pandas as pd
from geopy.geocoders import Nominatim
import json

# 

# create map object
m = folium.Map(location = [51, 10], zoom_start =  6)

fg = folium.FeatureGroup()

# global tooltip
tooltip = "Für weitere Infos klicken!"

# create GeoJSON layer
geojson = folium.GeoJson(
                'testDocuments.geojson',
                name = 'geojson',
            ).add_to(m)

# add search box
fg.add_to(m)
folium.plugins.Search(geojson, search_label = 'name').add_to(m)

# Generate map
m.save('VEJMap.html')
