import requests
import os
import zipfile
import io
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import folium 
from folium.plugins import MarkerCluster

# ==============================
# Descargar Shapefile de Natural Earth para utilizar en GeoPandas
# ==============================

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

shp_file = os.path.join(DATA_DIR, "ne_110m_admin_0_countries.shp")

if not os.path.exists(shp_file):
    print("Descargando shapefile de Natural Earth...")
    url_shp = "https://naturalearth.s3.amazonaws.com/110m_cultural/ne_110m_admin_0_countries.zip"
    r = requests.get(url_shp)
    if r.status_code == 200:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        z.extractall(DATA_DIR)
        print("Shapefile descargado y extraído en carpeta 'data/'")
    else:
        raise Exception("No se pudo descargar el shapefile. Verificá la URL o tu conexión.")
else:
    print("Shapefile ya disponible en 'data/'")

# ==============================
# Descargar datos de la API
# ==============================

# Fechas de Busqueda
fechaI = "2015-01-01"
fechaF = "2025-01-01"

#Ubicacion de busqueda
latitudS = -56  # Latitud Sur
latitudN = -15  # Latitud Norte
longitudO = -75  # Longitud Oeste
longitudE = -34  # Longitud Este

#Limite de resultados
limite = 20000

# URL de API de Argentina + Paises Limitrofes
url = ("https://earthquake.usgs.gov/fdsnws/event/1/query"
    f"?format=geojson&starttime={fechaI}&endtime={fechaF}"
    f"&minlatitude={latitudS}&maxlatitude={latitudN}&minlongitude={longitudO}&maxlongitude={longitudE}"
    f"&limit={limite}")

# ==============================
# Descargar datos
# ==============================
print("Descargando datos...")
response = requests.get(url)
data = response.json()

# ==============================
# Procesar datos en DataFrame
# ==============================

# Extraer eventos
features = data["features"]

# Armar lista de diccionarios
terremotos = []
for f in features:
    props = f["properties"]
    coords = f["geometry"]["coordinates"]
    terremotos.append({
        "Lugar": props["place"],
        "Magnitud": props["mag"],
        "Tiempo": pd.to_datetime(props["time"], unit="ms"),
        "Longitud": coords[0],
        "Latitud": coords[1],
        "Profundidad_km": coords[2],
        "URL": props["url"]
    })

# Convertir a DataFrame
df = pd.DataFrame(terremotos)

# Mostrar cantidad y primeras filas
print(f"Cantidad total de terremotos descargados: {len(df)}")

# ==============================
# Grafico temporal de los resultados
# ==============================

df["Año"] = df["Tiempo"].dt.year

conteoAnual = df.groupby("Año")["Magnitud"].count()

plt.figure(figsize=(10,5))
conteoAnual.plot(kind="bar", color="steelblue", edgecolor="black")
plt.title("Cantidad de sismos por Año en Argentina y Países Limitrofes (2015-2025)")
plt.xlabel("Año")
plt.ylabel("Cantidad de Sismos")
plt.xticks(rotation=45)
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()

# ==============================
# Mapa geografico con GeoPandas
# ==============================

# Cargar mapa base
planeta = gpd.read_file(shp_file)

# Filtrar Sudamerica
sudamerica = planeta[planeta["CONTINENT"] == "South America"]

# Mapa de argentina y limitrofes
paises = ["Argentina", "Chile", "Uruguay", "Paraguay", "Bolivia", "Brazil"]
subset = sudamerica[sudamerica["NAME"].isin(paises)]

# Convertir DataFrame a GeoDataFrame
gdf = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df.Longitud, df.Latitud), crs="EPSG:4326"
)

# Grafico
fig, ax = plt.subplots(figsize=(8,8))
subset.plot(ax=ax, color="white", edgecolor="black")
gdf.plot(
    ax=ax,
    markersize=df["Magnitud"]*2,
    color="red",
    alpha=0.6,
)
plt.title("Mapa de Sismos en Argentina y Países Limitrofes (2015-2025)")
plt.show()

# ==============================
# Desarrollo de Mapa Interactivo con Folium
# ==============================
m = folium.Map(location=[-34.6, -58.4], zoom_start=4)

# Diccionario para cada año
años = sorted(df["Año"].unique())
años_grupos = {}

for año in años:
    fg = folium.FeatureGroup(name=str(año))
    años_grupos[año] = fg
    m.add_child(fg)

# Añadir puntos de sismos a la capa correspondiente
for idx, row in df.iterrows():
    colores_magnitud = "green" if row["Magnitud"] < 4 else "orange" if row["Magnitud"] < 5 else "red"
    folium.CircleMarker(
        location=[row["Latitud"], row["Longitud"]],
        radius=row["Magnitud"] * 2,
        color=colores_magnitud,
        fill=True,
        fill_opacity=0.6,
        popup=(
            f"<b>Lugar:</b> {row['Lugar']}<br>"
            f"<b>Magnitud:</b> {row['Magnitud']}<br>"
            f"<b>Profundidad:</b> {row['Profundidad_km']} km<br>"
            f"<b>Fecha:</b> {row['Tiempo'].strftime('%Y-%m-%d')}"
        )
    ).add_to(años_grupos[row["Año"]])

# Añadir control de capas
folium.LayerControl(collapsed=False).add_to(m)

# Guardar mapa en formato HTML
m.save("mapa_sismos_interactivo.html")
print("Mapa interactivo guardado como 'mapa_sismos_interactivo.html'")


