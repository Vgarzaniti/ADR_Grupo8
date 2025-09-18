import requests
import pandas as pd

# URL de la API sin límite
url = "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"

# Descargar datos
response = requests.get(url)
data = response.json()

# Extraer eventos
features = data["features"]

# Armar lista de diccionarios
terremotos = []
for f in features:
    props = f["properties"]
    terremotos.append({
        "Lugar": props["place"],
        "Magnitud": props["mag"],
        "Tiempo": pd.to_datetime(props["time"], unit="ms"),
        "URL": props["url"]
    })

# Convertir a DataFrame
df = pd.DataFrame(terremotos)

# Mostrar cantidad y primeras filas
print("Cantidad total de terremotos descargados:", len(df))
print(df.head())
