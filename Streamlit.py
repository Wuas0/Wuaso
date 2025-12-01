import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(page_title="Mapa de Postes Ruta 5 Sur", layout="wide")

st.title("Mapa de Postes en la Ruta 5 Sur (Los Ángeles - Temuco)")


# Coordenadas aproximadas de inicio y fin de la Ruta 5 Sur
start_lat, start_lon = -37.4697, -72.3537  # Los Ángeles
end_lat, end_lon = -38.7359, -72.5904      # Temuco

# Cargar el archivo CSV
csv_path = "postes_con_coordenadas2.csv"
df = pd.read_csv(csv_path)

# Cargar teléfonos SOS
sos_path = "telefonos_sos.csv"
sos_df = pd.read_csv(sos_path)

def clean_km(km):
    return float(str(km).replace(',', '.').replace('"', ''))

df['kilometro'] = df['kilometro'].apply(clean_km)

min_km = df['kilometro'].min()
max_km = df['kilometro'].max()

def interpolate_coord(km, min_km, max_km, start, end):
    return start + (end - start) * ((km - min_km) / (max_km - min_km))

df['latitud_estimada'] = df['kilometro'].apply(lambda km: interpolate_coord(km, min_km, max_km, start_lat, end_lat))
df['longitud_estimada'] = df['kilometro'].apply(lambda km: interpolate_coord(km, min_km, max_km, start_lon, end_lon))

# Mostrar tabla de datos

# Botones para mostrar/ocultar orientación

# Botón para mostrar/ocultar tabla de datos de los postes
st.subheader("Datos de los postes")
if 'mostrar_postes' not in st.session_state:
    st.session_state['mostrar_postes'] = False
if st.button("Mostrar/Ocultar datos de postes"):
    st.session_state['mostrar_postes'] = not st.session_state['mostrar_postes']

# Botones para mostrar/ocultar orientación
cols = ['N°Poste', 'kilometro', 'Posicion', 'latitud_estimada', 'longitud_estimada']
if st.session_state['mostrar_postes']:
    st.dataframe(df[cols])

# Crear el mapa

# Botones para filtrar orientación en el mapa

st.subheader("Filtrar postes en el mapa por orientación")
orientacion = st.radio(
    "Selecciona orientación:",
    options=["Ambos", "P", "O"],
    horizontal=True
)
if orientacion == "P":
    df_mapa = df[df['Posicion'] == 'P']
elif orientacion == "O":
    df_mapa = df[df['Posicion'] == 'O']
else:
    df_mapa = df

center_lat = (start_lat + end_lat) / 2
center_lon = (start_lon + end_lon) / 2
m = folium.Map(location=[center_lat, center_lon], zoom_start=8)

# Función para encontrar la localidad SOS más cercana
def localidad_mas_cercana(lat, lon, sos_df):
    dists = np.sqrt((sos_df['latitud'] - lat)**2 + (sos_df['longitud'] - lon)**2)
    idx = dists.idxmin()
    return sos_df.loc[idx]

for _, row in df_mapa.iterrows():
    localidad = localidad_mas_cercana(row['latitud_estimada'], row['longitud_estimada'], sos_df)
    popup_text = (
        f"Poste {row['N°Poste']}<br>Km {row['kilometro']}<br>{row['Posicion']}<br>"
        f"SOS: {localidad['localidad']}<br>Teléfono: {localidad['telefono_sos']}"
    )
    # Color: rojo si N°Poste par, azul si impar
    try:
        num_poste = int(row['N°Poste'])
    except Exception:
        num_poste = 0
    color = 'red' if num_poste % 2 == 0 else 'blue'
    folium.Marker(
        location=[row['latitud_estimada'], row['longitud_estimada']],
        popup=popup_text,
        icon=folium.Icon(color=color, icon='info-sign')
    ).add_to(m)


# Mostrar mapa y tabla de teléfonos SOS en columnas

col1, col2 = st.columns([2, 1])
with col1:
    st.subheader("Mapa de Postes Estimados")
    st_folium(m, width=900, height=700)
    # Botón para ir al reporte
    if st.button("Ir a generar reporte"):
        st.session_state['ir_a_reporte'] = True
with col2:
    st.subheader("Servicios Grúas por Localidad")
    if 'mostrar_gruas' not in st.session_state:
        st.session_state['mostrar_gruas'] = False
    if st.button("Mostrar/Ocultar servicios grúas"):
        st.session_state['mostrar_gruas'] = not st.session_state['mostrar_gruas']
    if st.session_state['mostrar_gruas']:
        st.dataframe(sos_df[['localidad', 'telefono_sos']])

# Formulario de reporte de errores

# Mostrar el formulario solo si se presionó el botón o por defecto
if 'ir_a_reporte' not in st.session_state:
    st.session_state['ir_a_reporte'] = False
if st.session_state['ir_a_reporte']:
    st.subheader("Reportar error en un poste")
    with st.form("reporte_form"):
        poste_id = st.selectbox("Selecciona el poste", df['N°Poste'].astype(str))
        error_text = st.text_area("Describe el error encontrado")
        submitted = st.form_submit_button("Enviar reporte")
    if submitted:
        st.subheader("Califica la aplicación")
        sentiment_mapping = ["one", "two", "three", "four", "five"]
        selected = st.feedback("stars")
        calificacion = None
        if selected is not None:
            calificacion = selected + 1
            st.markdown(f"Seleccionaste {sentiment_mapping[selected]} estrella(s). ¡Gracias por tu feedback!")

        reporte = pd.DataFrame({
            'N°Poste': [poste_id],
            'error': [error_text],
            'calificacion': [calificacion if calificacion is not None else '']
        })
        try:
            reportes = pd.read_csv("reportes_postes.csv")
            reportes = pd.concat([reportes, reporte], ignore_index=True)
        except FileNotFoundError:
            reportes = reporte
        reportes.to_csv("reportes_postes.csv", index=False)
        st.success("¡Reporte enviado correctamente!")
        st.session_state['ir_a_reporte'] = False


# Fin del formulario

# Mostrar todos los reportes enviados fuera del formulario
st.subheader("Ver reportes enviados")
if st.button("Mostrar reportes de postes"):
    try:
        reportes = pd.read_csv("reportes_postes.csv")
        st.dataframe(reportes)
    except FileNotFoundError:
        st.info("No hay reportes registrados todavía.")

