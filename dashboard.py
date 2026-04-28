import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import altair as alt

# Dynamic today
TODAY = datetime.now()

# Google Sheets IDs
SHEET_ID = "1ztQKIs8KNf5QZPPDItP9S63JvrmIgCmiQvFLtIKm74k"
HOJA1_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1491104641"
HOJA2_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=943820696"

# Page Configuration
st.set_page_config(page_title="Logistics Dashboard - Taco 2026", page_icon="🚚", layout="wide")

def create_static_bar_chart(data, x_col, y_col):
    return alt.Chart(data).mark_bar(color='#58a6ff').encode(
        x=alt.X(f'{x_col}:N', title=x_col),
        y=alt.Y(f'{y_col}:Q', title=y_col),
        tooltip=[x_col, y_col]
    ).properties(width='container', height=300).configure_axis(labelColor='#c9d1d9', titleColor='#c9d1d9')

@st.cache_data(ttl=300)
def load_and_process_data():
    try:
        df1 = pd.read_csv(HOJA1_URL)
        df2 = pd.read_csv(HOJA2_URL)
    except Exception as e:
        st.error(f"Error conectando a GSheets: {e}")
        st.stop()

    # Helper to find column by name or approximate index
    def get_col(df, idx, keywords):
        if idx < len(df.columns):
            col_name = df.columns[idx]
            if any(k.lower() in col_name.lower() for k in keywords): return col_name
        for col in df.columns:
            if any(k.lower() in col.lower() for k in keywords): return col
        return df.columns[idx] if idx < len(df.columns) else None

    # Mapping based on your Excel letters
    C_NIC = get_col(df1, 2, ['NIC'])
    H_NP_ALTA = get_col(df1, 7, ['NP Alta', 'Fecha y hora'])
    O_FACTURA = get_col(df1, 14, ['Comprobante', 'Fecha y Hora'])
    R_DESTINO = get_col(df1, 17, ['Destinatario', 'Nombre'])
    S_FECHA = get_col(df1, 18, ['Fecha'])
    AB_DESPACHO = get_col(df1, 27, ['LR Fecha', 'Hora'])
    L_APROB = get_col(df1, 11, ['NP de aprob', 'final'])

    # 1. NIC Cleaning (Logic AI & AJ)
    def clean_nic(val):
        val = str(val).replace(" ", "").strip()
        if val.isdigit() and len(val) > 9:
            # Excel MID(val, 4, len-7) is Python val[3 : -4]
            return val[3:-4]
        return val
    df1['NIC_CLEAN'] = df1[C_NIC].apply(clean_nic)

    # 2. Hoja2 Lookup (Logic AK & AL)
    # B(1) is NIC, F(5) is Recibe, O(14) is Entrega
    h2 = df2.iloc[:, [1, 5, 14]].copy()
    h2.columns = ['NIC_H2', 'AK_RECIBE', 'AL_ENTREGA']
    h2['NIC_H2'] = h2['NIC_H2'].astype(str).str.strip()
    
    df = df1.merge(h2, left_on='NIC_CLEAN', right_on='NIC_H2', how='left')

    # 3. Date Conversion
    for col in [H_NP_ALTA, O_FACTURA, S_FECHA, AB_DESPACHO, 'AK_RECIBE']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

    # 4. AF: Zone Logic
    def get_zone(val):
        v = str(val).lower()
        if "cruz del sur" in v: return "CDS"
        if any(x in v for x in ["kergaravat", "administracion", "freiria", "rejon"]): return "AMBA"
        return "Interior"
    df['ZONA'] = df[R_DESTINO].apply(get_zone)

    # 5. AG: Status Logic
    def get_status(row):
        if pd.notnull(row[AB_DESPACHO]): return "Despachado"
        if pd.notnull(row[S_FECHA]): return "Pendiente de despacho"
        if pd.notnull(row[O_FACTURA]): return "Pendiente de armado"
        return "S/D"
    df['ESTADO'] = df.apply(get_status, axis=1)

    # 6. AH, AM, AN, AO Calculations
    # AH: Days NP/LR (AB - H)
    df['DIAS_NP_LR'] = (df[AB_DESPACHO] - df[H_NP_ALTA]).dt.days
    
    # AK/AL for CDS
    df['AL_TEXT'] = df['AL_ENTREGA'].astype(str).str.lower()
    df['AL_DATE'] = pd.to_datetime(df['AL_ENTREGA'], dayfirst=True, errors='coerce')
    
    # AM: Days CDS (AL - AK)
    df['DIAS_CDS'] = (df['AL_DATE'] - df['AK_RECIBE']).dt.days
    
    # AN: Pendientes (Today - AK) if AL contains "pendiente"
    df['DIAS_PENDIENTES_CDS'] = np.where(
        (df['AL_TEXT'].str.contains('pendiente')) & (pd.notnull(df['AK_RECIBE'])),
        (TODAY - df['AK_RECIBE']).dt.days,
        np.nan
    )
    
    # AO: Tiempos Logistica (AB - O)
    df['TIEMPO_LOGISTICA'] = (df[AB_DESPACHO] - df[O_FACTURA]).dt.days

    # Map to Dashboard Names
    df['AMBA/INTERIOR'] = df['ZONA']
    df['estado de pedido'] = df['ESTADO']
    df['Dias NP/LR'] = df['DIAS_NP_LR']
    df['dias de entrega'] = df['DIAS_CDS']
    df['Pendientes'] = df['DIAS_PENDIENTES_CDS']
    df['Tiempos Logistica'] = df['TIEMPO_LOGISTICA']
    df['CDS recibe'] = df['AK_RECIBE']
    df['CDS entrega'] = df['AL_ENTREGA']
    df['Comprobante Fecha y Hora'] = df[O_FACTURA]
    df['LR Fecha y Hora '] = df[AB_DESPACHO]
    
    return df, {'NP_ALTA': H_NP_ALTA, 'NP_APROB': L_APROB}

def main():
    st.markdown("""<style>.stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }</style>""", unsafe_allow_html=True)
    df, cmap = load_and_process_data()
    
    st.title("🚚 Dashboard de Logística")
    st.sidebar.button("🔄 Sincronizar GSheets", on_click=st.cache_data.clear)

    tab1, tab2, tab3 = st.tabs(["🔍 Buscador", "⚙️ Tiempos operativos", "📍 CDS"])

    with tab1:
        sq = st.text_input("Buscar Pedido, Cliente o Remito").strip()
        if sq:
            mask = df['Nro de Pedido'].astype(str).str.endswith(sq) | df['Cliente'].astype(str).str.contains(sq, case=False) | df['Remito'].astype(str).str.contains(sq, case=False)
            if len(sq) > 7: mask |= df['NIC_CLEAN'].astype(str).str.contains(sq)
            res = df[mask].drop_duplicates(subset=['Nro de Pedido', 'Remito'])
            for _, r in res.iterrows():
                with st.container():
                    st.markdown(f"### {r['Cliente']} | Pedido: {r['Nro de Pedido']}")
                    st.write(f"**Estado:** {r['estado de pedido']} | **Zona:** {r['AMBA/INTERIOR']}")
                    st.write(f"📅 Alta: {r[cmap['NP_ALTA']].strftime('%d/%m/%Y') if pd.notnull(r[cmap['NP_ALTA']]) else 'S/D'} | 🚚 Despacho: {r['LR Fecha y Hora '].strftime('%d/%m/%Y') if pd.notnull(r['LR Fecha y Hora ']) else 'S/D'}")
                    if r['AMBA/INTERIOR'] == 'CDS':
                        st.write(f"📍 CDS Recibe: {r['CDS recibe'].strftime('%d/%m/%Y') if pd.notnull(r['CDS recibe']) else 'S/D'} | 🏁 Entrega: {r['CDS entrega']}")
                    st.markdown("---")

    with tab2:
        st.subheader("Pendientes de Gestión")
        c1, c2 = st.columns(2)
        c1.metric("Pendiente Armado", len(df[df['estado de pedido'] == "Pendiente de armado"]))
        c2.metric("Pendiente Despacho", len(df[df['estado de pedido'] == "Pendiente de despacho"]))
        
        st.markdown("---")
        st.subheader("Tiempos Promedio")
        avg_ah = df['Dias NP/LR'].mean()
        avg_ao = df['Tiempos Logistica'].mean()
        st.metric("Promedio NP a LR (Días)", f"{avg_ah:.2f}")
        st.metric("Promedio Logística (Factura a Despacho)", f"{avg_ao:.2f}")

    with tab3:
        st.subheader("Análisis CDS")
        if 'dias de entrega' in df.columns:
            st.metric("Promedio Días CDS", f"{df['dias de entrega'].mean():.2f}")
        
        st.markdown("---")
        st.subheader("📋 Pendientes CDS (> 10 días)")
        pend_cds = df[(df['AMBA/INTERIOR'] == 'CDS') & (df['Pendientes'] > 10)]
        if not pend_cds.empty:
            st.dataframe(pend_cds[['Nro de Pedido', 'Cliente', 'Pendientes']].sort_values('Pendientes', ascending=False), use_container_width=True)
        else: st.info("No hay pendientes críticos.")
        
        st.subheader("🚫 Anulados")
        anul = df[df['AL_TEXT'].str.contains('anulado', na=False)]
        if not anul.empty: st.dataframe(anul[['Nro de Pedido', 'Cliente', 'Remito']], use_container_width=True)
        else: st.info("No hay anulados.")

if __name__ == "__main__": main()
