from string import Template
import requests
import os
import zipfile
import io
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import folium 
from branca.element import Template, MacroElement
from folium.plugins import TimestampedGeoJson
import numpy as np
from scipy.stats import linregress


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
conteoAnual.plot(kind="bar", color="cornflowerblue", edgecolor="black")
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
    edgecolor="black",
    alpha=0.6,
)
plt.title("Mapa de Sismos en Argentina y Países Limitrofes (2015-2025)")
plt.show()

# ==============================
# Desarrollo de Mapa Interactivo con Folium + Timeline
# ==============================
m = folium.Map(location=[-34.6, -58.4], zoom_start=4)

def color_magnitud(magnitud):
    if 4 <= magnitud < 5:         # Ligero
        return 'green'
    elif 5 <= magnitud < 6:       # Moderado
        return 'yellow'
    elif 6 <= magnitud < 7:       # Fuerte
        return 'orange'
    elif 7 <= magnitud < 8:       # Mayor
        return 'red'
    elif magnitud >= 8:           # Épico o catastrófico
        return 'darkred'          
    else:
        return 'blue'            

# Crear capas por año
for year in sorted(df["Tiempo"].dt.year.unique()):
    capa = folium.FeatureGroup(name=f"Sismos {year}", show=False)
    subset = df[df["Tiempo"].dt.year == year]
    
    for _, row in subset.iterrows():
        folium.CircleMarker(
            location=[row["Latitud"], row["Longitud"]],
            radius=row["Magnitud"] * 2,
            color="black",
            weight=0.5,
            fill=True,
            fill_color=color_magnitud(row["Magnitud"]),
            fill_opacity=0.6,
            popup=(
                f"<b>Lugar:</b> {row['Lugar']}<br>"
                f"<b>Magnitud:</b> {row['Magnitud']}<br>"
                f"<b>Profundidad:</b> {row['Profundidad_km']} km<br>"
                f"<b>Fecha:</b> {row['Tiempo']}"
            )
        ).add_to(capa)
    
    capa.add_to(m)

# Contruccion del GeoJSON con timestamps
features = []
for _, row in df.iterrows():
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [row["Longitud"], row["Latitud"]],
        },
        "properties": {
            "time": row["Tiempo"].strftime("%Y-%m-%dT%H:%M:%S"),
            "popup": (
                f"<b>Lugar:</b> {row['Lugar']}<br>"
                f"<b>Magnitud:</b> {row['Magnitud']}<br>"
                f"<b>Profundidad:</b> {row['Profundidad_km']} km<br>"
                f"<b>Fecha</b> {row['Tiempo']}"
            ),
            "icon": "circle",
            "iconstyle": {
                "fillColor": color_magnitud(row["Magnitud"]),
                "fillOpacity": 0.6,
                "stroke": True,
                "color": "black",
                "weight": 0.5,
                "radius": row["Magnitud"] * 2
            }
        }
    })

TimestampedGeoJson(
    {"type": "FeatureCollection", "features": features},
    period="P1M",
    add_last_point=True,
    auto_play=False,
    loop=False,
    max_speed=1,
    loop_button=True,
    date_options="YYYY-MM-DD",
    time_slider_drag_update=True,
).add_to(m)

# Leyenda de colores por magnitudes
template = """
{% macro html(this, kwargs) %}
<div style="position: fixed; 
            bottom: 50px; left: 50px; width: 250px; height: 160px; 
            background-color: white; z-index:9999; font-size:14px;
            border:2px solid grey; border-radius:6px; padding: 10px;">
<b>Magnitud</b><br>
&nbsp;<i class="fa fa-circle" style="color:blue"></i>&nbsp; < 4.0<br>
&nbsp;<i class="fa fa-circle" style="color:green"></i>&nbsp; 4.0 - 4.9 (Ligero)<br>
&nbsp;<i class="fa fa-circle" style="color:yellow"></i>&nbsp; 5.0 - 5.9 (Moderado)<br>
&nbsp;<i class="fa fa-circle" style="color:orange"></i>&nbsp; 6.0 - 6.9 (Fuerte)<br>
&nbsp;<i class="fa fa-circle" style="color:red"></i>&nbsp; 7.0 - 7.9 (Mayor)<br>
&nbsp;<i class="fa fa-circle" style="color:darkred"></i>&nbsp; ≥ 8.0 (Épico/Catastrófico)
</div>
{% endmacro %}
"""

macro = MacroElement()
macro._template = Template(template)
m.get_root().add_child(macro)
folium.LayerControl(collapsed=False).add_to(m)

# Guardar mapa en formato HTML
m.save("mapa_sismos_interactivo.html")
print("Mapa interactivo guardado como 'mapa_sismos_interactivo.html'")


# ==============================
# Desarrollo de grafico con clasificacion de sismos en DataFrame
# ==============================

df["Categoria"] = pd.cut (
    df["Magnitud"],
    bins=[0, 4, 6, 10],
    labels=["Leves (<4)", "Moderados (4-6)", "Fuertes (≥6)"]
)

conteo_categorias = df.groupby(["Año", "Categoria"], observed=False)["Magnitud"].count().unstack(fill_value=0)

conteo_categorias.plot(kind="bar", stacked=False, figsize=(12,6), color=["#3a1fb4", "#2ca073", "#ff5a0e"], edgecolor="black", width=0.8)
plt.title("Evolución de sismos leves, moderados y fuertes (2015-2025)") 
plt.xlabel("Año")
plt.ylabel("Cantidad de Sismos")
plt.xticks(rotation=45)
plt.legend(title="Categoría")
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()

# ==============================
# Aplicación y desarrollo de Ley de Gutenberg-Richter (Frecuencia-Magnitud)
# ==============================

# Calcular frecuencia acumulada
magnitudes = np.arange(3, df["Magnitud"].max() + 0.5, 0.5)
frecuencias = [np.sum(df["Magnitud"] >= m) for m in magnitudes]

# Filtrar para evitar log10(0)
magnitudes_validas = []
logN_validas = []
for m, f in zip(magnitudes, frecuencias):
    if f > 0:
        magnitudes_validas.append(m)
        logN_validas.append(np.log10(f))

magnitudes_validas = np.array(magnitudes_validas)
logN_validas = np.array(logN_validas)

# Ajuste lineal logN = a - bM
slope, intercept, r_value, p_value, std_err = linregress(magnitudes_validas, logN_validas)

# Generar línea de ajuste
ajuste = intercept + slope * magnitudes_validas

plt.figure(figsize=(8,6))
plt.scatter(magnitudes_validas, logN_validas, color="indigo", label="Datos observados")
plt.plot(magnitudes_validas, ajuste, color="red", label=f"Ajuste: logN = {intercept:.2f} {slope:+.2f}M")
plt.title("Ley de Gutenberg–Richter (2015–2025)")
plt.xlabel("Magnitud (M)")
plt.ylabel("Frecuencia acumulada log10(N ≥ M)")
plt.grid(True, which="both", linestyle="--", alpha=0.7)
plt.legend()
plt.show()

# Resultado de ajuste
print(f"Intercepto (a): {intercept:.3f}")
print(f"Pendiente (b): {-slope:.3f}")
print(f"R² del ajuste: {r_value**2:.3f}")
