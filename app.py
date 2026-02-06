import streamlit as st
import pandas as pd
import numpy as np
import requests
import pydeck as pdk
import plotly.express as px

GOOGLE_API_KEY = "AIzaSyB9HnuqmxpmNi-CpepHUz9KUgsPemrwaF4"

# -----------------------------
# Funciones
# -----------------------------
def geocodificar_google(direccion):
    if not direccion:
        return None, None
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": direccion, "key": GOOGLE_API_KEY, "region": "co"}
    try:
        resp = requests.get(url, params=params).json()
        if resp["status"] == "OK":
            loc = resp["results"][0]["geometry"]["location"]
            return loc["lat"], loc["lng"]
        return None, None
    except:
        return None, None

def limpiar_direccion_avanzada(direccion, ciudad=""):
    """Normaliza direcciones de forma avanzada"""
    if pd.isna(direccion):
        direccion = ""
    direccion = direccion.strip().replace("\n", " ").replace("  ", " ")
    direccion = direccion.replace("Cra ", "Carrera ").replace("Cra.", "Carrera ")
    direccion = direccion.replace("Cl ", "Calle ").replace("Cl.", "Calle ")
    direccion = direccion.replace("Av ", "Avenida ").replace("Av.", "Avenida ")
    direccion = " ".join([p.capitalize() for p in direccion.split()])
    if ciudad and ciudad.strip():
        ciudad_clean = " ".join([p.capitalize() for p in ciudad.strip().split()])
        direccion_completa = f"{direccion}, {ciudad_clean}"
    else:
        direccion_completa = direccion
    return direccion_completa

def definir_color_estado(estado, activo_color, inactivo_color):
    """Devuelve color RGBA según estado"""
    if pd.isna(estado):
        return [200, 200, 200, 160]
    estado_str = str(estado).strip().lower()
    if estado_str == "activo":
        return [int(activo_color[1:3],16), int(activo_color[3:5],16), int(activo_color[5:7],16), 160]
    else:
        return [int(inactivo_color[1:3],16), int(inactivo_color[3:5],16), int(inactivo_color[5:7],16), 160]

# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="Geocodificador Google Colombia", layout="wide")
st.title("📍 Geocodificación Google – Colombia")

# Sidebar
st.sidebar.header("⚙️ Configuración de columnas")
st.sidebar.markdown("Define los nombres de las columnas de tu archivo Excel:")
col_rep_legal = st.sidebar.text_input("Columna Rep Legal", "rep legal")
col_telefono = st.sidebar.text_input("Columna Teléfono", "telefono")
col_direccion = st.sidebar.text_input("Columna Dirección", "direccion")
col_ciudad = st.sidebar.text_input("Columna Ciudad", "ciudad")
col_estado = st.sidebar.text_input("Columna Estado", "estado")

st.sidebar.header("🎨 Visualización por Estado")
estado_activo_color = st.sidebar.color_picker("Color para registros ACTIVOS", "#00B400")
estado_inactivo_color = st.sidebar.color_picker("Color para registros INACTIVOS", "#FF0000")

# Subir archivo
archivo = st.file_uploader("📁 Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if archivo:
    df = pd.read_excel(archivo)
    df.columns = [c.strip().lower() for c in df.columns]

    # Validar columnas
    for c in [col_rep_legal, col_telefono, col_direccion, col_ciudad, col_estado]:
        if c not in df.columns:
            df[c] = ""
            st.warning(f"No se encontró la columna '{c}', se llenará con vacíos.")

    # Sanitización avanzada de direcciones
    df["direccion_completa"] = df.apply(lambda row: limpiar_direccion_avanzada(row[col_direccion], row[col_ciudad]), axis=1)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Datos Originales", "🔍 Filtros", "🚀 Geocodificación", "🗺️ Mapa"])

    # -----------------------------
    # TAB 1: Datos Originales y Estadísticas
    # -----------------------------
    with tab1:
        st.subheader("📄 Vista previa de datos originales")
        st.dataframe(df, use_container_width=True)

        # Estadísticas por Estado
        st.subheader("📊 Estadísticas de registros por Estado")
        conteo_estado = df[col_estado].value_counts().reset_index()
        conteo_estado.columns = ["Estado", "Cantidad"]

        # Asignar color según estado
        color_map = {
            row["Estado"]: definir_color_estado(row["Estado"], estado_activo_color, estado_inactivo_color)
            for _, row in conteo_estado.iterrows()
        }

        fig = px.bar(
            conteo_estado,
            x="Estado",
            y="Cantidad",
            text="Cantidad",
            color="Estado",
            color_discrete_map={k: f"rgb({v[0]},{v[1]},{v[2]})" for k, v in color_map.items()}
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------
    # TAB 2: Filtros
    # -----------------------------
    with tab2:
        st.subheader("Filtros de datos")
        estados_disponibles = df[col_estado].dropna().unique().tolist()
        ciudades_disponibles = df[col_ciudad].dropna().unique().tolist()

        estado_filtro = st.multiselect("Filtrar por Estado", estados_disponibles, default=estados_disponibles)
        ciudad_filtro = st.multiselect("Filtrar por Ciudad", ciudades_disponibles, default=ciudades_disponibles)

        df_filtrado = df.copy()
        if estado_filtro:
            df_filtrado = df_filtrado[df_filtrado[col_estado].isin(estado_filtro)]
        if ciudad_filtro:
            df_filtrado = df_filtrado[df_filtrado[col_ciudad].isin(ciudad_filtro)]

        st.info(f"{len(df_filtrado)} registros después de aplicar filtros")
        st.dataframe(df_filtrado, use_container_width=True)

    # -----------------------------
    # TAB 3: Geocodificación
    # -----------------------------
    with tab3:
        st.subheader("Geocodificar direcciones filtradas")
        if st.button("🚀 Geocodificar"):
            if df_filtrado.empty:
                st.error("No hay datos para geocodificar")
            else:
                st.info(f"Geocodificando {len(df_filtrado)} direcciones...")

                latitudes, longitudes = [], []
                bar = st.progress(0)
                total = len(df_filtrado)

                for idx, direccion in enumerate(df_filtrado["direccion_completa"]):
                    lat, lon = geocodificar_google(direccion)
                    latitudes.append(lat)
                    longitudes.append(lon)
                    bar.progress((idx+1)/total)

                df_filtrado["latitud"] = latitudes
                df_filtrado["longitud"] = longitudes
                df_filtrado["color_rgb"] = df_filtrado[col_estado].apply(
                    lambda x: definir_color_estado(x, estado_activo_color, estado_inactivo_color)
                )

                st.success("✅ Geocodificación completada")
                st.session_state["df_mapa"] = df_filtrado  # Guardar para tab de mapa

                st.subheader("Datos geocodificados")
                st.dataframe(df_filtrado, use_container_width=True)
                csv = df_filtrado.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar CSV geocodificado", data=csv, file_name="datos_geocodificados.csv", mime="text/csv")

    # -----------------------------
    # TAB 4: Mapa optimizado
    # -----------------------------
    with tab4:
        if "df_mapa" not in st.session_state or st.session_state["df_mapa"].empty:
            st.warning("Mapa disponible después de geocodificar en el Tab '🚀 Geocodificación'")
        else:
            df_mapa = st.session_state["df_mapa"].dropna(subset=["latitud", "longitud"]).copy()

            # Asegurarse de que lat/lon sean float
            df_mapa["latitud"] = df_mapa["latitud"].astype(float)
            df_mapa["longitud"] = df_mapa["longitud"].astype(float)

            # Formatear color como lista de 4 enteros (RGBA)
            df_mapa["color_rgb"] = df_mapa["color_rgb"].apply(
                lambda x: [int(c) for c in x] if isinstance(x, (list, tuple)) else [200,200,200,160]
            )

            # Calcular centro y zoom automático
            lat_mean = df_mapa["latitud"].mean()
            lon_mean = df_mapa["longitud"].mean()
            lat_min, lat_max = df_mapa["latitud"].min(), df_mapa["latitud"].max()
            lon_min, lon_max = df_mapa["longitud"].min(), df_mapa["longitud"].max()
            lat_range = lat_max - lat_min
            lon_range = lon_max - lon_min
            max_range = max(lat_range, lon_range)
            zoom = 6
            if max_range > 0:
                zoom = max(1, min(12, 6 - np.log2(max_range)))

            # Crear la capa de Scatterplot
            layer = pdk.Layer(
                "ScatterplotLayer",
                df_mapa,
                get_position=["longitud", "latitud"],
                get_fill_color="color_rgb",
                get_radius=30,
                radius_min_pixels=3,
                radius_max_pixels=10,
                pickable=True
            )

            # Estado inicial de la vista
            view_state = pdk.ViewState(
                latitude=lat_mean,
                longitude=lon_mean,
                zoom=zoom,
                pitch=0
            )

            # Tooltip personalizado
            tooltip = {
                "html": (
                    f"<b>Rep Legal:</b> {{{col_rep_legal}}} <br>"
                    f"<b>Teléfono:</b> {{{col_telefono}}} <br>"
                    f"<b>Dirección:</b> {{direccion_completa}} <br>"
                    f"<b>Estado:</b> {{{col_estado}}}"
                ),
                "style": {"backgroundColor": "white", "color": "black", "fontSize": "12px", "padding": "5px"}
            }

            st.subheader("🗺️ Mapa de Ubicaciones")
            st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, tooltip=tooltip))
