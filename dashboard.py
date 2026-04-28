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
st.set_page_config(
    page_title="Logistics Dashboard - Taco 2026",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design
st.markdown("""
<style>
.main { background-color: #0d1117; }
[data-testid="stMetricValue"] { color: #58a6ff !important; font-size: 1.8rem !important; }
[data-testid="stMetricLabel"] { color: #c9d1d9 !important; font-weight: bold !important; }
.stMetric {
    background-color: #161b22;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #30363d;
    box-shadow: 0 4px 6px rgba(0,0,0,0.4);
}
h1, h2, h3 { color: #58a6ff; }
.stDataFrame { border-radius: 10px; }
.last-update { color: #8b949e; font-size: 0.9rem; margin-bottom: 20px; }

.search-card {
    background-color: #161b22;
    border: 1px solid #30363d;
    padding: 25px;
    border-radius: 15px;
    margin-bottom: 25px;
    box-shadow: 0 8px 16px rgba(0,0,0,0.4);
}
.card-header h3 { margin: 0; color: #f0f6fc; font-size: 1.5rem; }
.card-subtitle { color: #58a6ff; font-size: 1rem; margin-top: 5px; margin-bottom: 20px; }

.timeline-container {
    border-left: 2px solid #30363d;
    margin-left: 15px;
    padding-left: 25px;
    position: relative;
    margin-top: 10px;
}
.timeline-item {
    position: relative;
    padding-bottom: 15px;
    color: #c9d1d9;
    font-size: 1.05rem;
}
.timeline-item::before {
    content: '';
    position: absolute;
    left: -32px;
    top: 5px;
    width: 12px;
    height: 12px;
    background-color: #58a6ff;
    border-radius: 50%;
    border: 3px solid #161b22;
}
.timeline-item b { color: #f0f6fc; }
.summary-box {
    background-color: #0d1117;
    padding: 15px;
    border-radius: 8px;
    margin-top: 15px;
    border-left: 4px solid #58a6ff;
    color: #c9d1d9;
}
</style>
""", unsafe_allow_html=True)

def create_static_bar_chart(data, x_col, y_col):
    return alt.Chart(data).mark_bar(color='#58a6ff').encode(
        x=alt.X(f'{x_col}:N', title=x_col),
        y=alt.Y(f'{y_col}:Q', title=y_col),
        tooltip=[x_col, y_col]
    ).properties(width='container', height=300).configure_axis(labelColor='#c9d1d9', titleColor='#c9d1d9').configure_view(strokeOpacity=0)

@st.cache_data(ttl=300)
def load_and_process_data():
    try:
        df = pd.read_csv(HOJA1_URL, low_memory=False)
    except Exception as e:
        st.error(f"Error conectando a GSheets: {e}")
        st.stop()

    def find_col(idx, default_name):
        if idx < len(df.columns):
            return df.columns[idx]
        return default_name

    # Column Mapping by Index
    MAP_COLS = {
        'NP_ALTA': find_col(7, 'NP Alta -Fecha y hora '),
        'NP_APROB': find_col(11, 'NP de aprobaci\u00f3n final -Fecha y hora '),
        'FACTURA': find_col(14, 'Comprobante Fecha y Hora'), # O
        'BULTOS': find_col(16, 'Cantidad de Bultos'), # Q
        'DESPACHO': find_col(27, 'LR Fecha y Hora '), # AB
        'ZONA': find_col(31, 'AMBA/INTERIOR'),
        'ESTADO_SHEET': find_col(32, 'estado de pedido'),
        'DIAS_NP_LR': find_col(33, 'Dias NP/LR'),
        'CDS_RECIBE': find_col(36, 'CDS recibe'),
        'CDS_ENTREGA': find_col(37, 'CDS entrega'),
        'DIAS_CDS': find_col(38, 'dias de entrega'),
        'PENDIENTES_CDS': find_col(39, 'Pendientes'),
        'TIEMPO_LOG': find_col(40, 'Tiempos Logistica')
    }

    # Status Logic (as requested)
    # Pendiente Armado: Column Q (Bultos) is null or 0
    # Pendiente Despacho: Column AB (LR) is null but has Bultos > 0
    def get_custom_status(row):
        bultos = pd.to_numeric(row[MAP_COLS['BULTOS']], errors='coerce')
        if pd.notnull(row[MAP_COLS['DESPACHO']]): return "Despachado"
        if pd.notnull(bultos) and bultos > 0: return "Pendiente de despacho"
        if pd.notnull(row[MAP_COLS['FACTURA']]): return "Pendiente de armado"
        return "S/D"
    
    df['estado de pedido'] = df.apply(get_custom_status, axis=1)

    # Date Conversion for DISPLAY
    cmap = {}
    # NP/Factura/Despacho columns are M/D/YY (American)
    for key in ['NP_ALTA', 'NP_APROB', 'FACTURA', 'DESPACHO']:
        col_name = MAP_COLS[key]
        new_col = key + '_DT'
        df[new_col] = pd.to_datetime(df[col_name], dayfirst=False, errors='coerce')
        cmap[key] = new_col
    
    # CDS columns are DD/MM/YYYY (European)
    for key in ['CDS_RECIBE', 'CDS_ENTREGA']:
        col_name = MAP_COLS[key]
        new_col = key + '_DT'
        df[new_col] = pd.to_datetime(df[col_name], dayfirst=True, errors='coerce')
        cmap[key] = new_col

    # Consistency names
    df['AMBA/INTERIOR'] = df[MAP_COLS['ZONA']]
    df['Dias NP/LR'] = pd.to_numeric(df[MAP_COLS['DIAS_NP_LR']], errors='coerce')
    df['dias de entrega'] = pd.to_numeric(df[MAP_COLS['DIAS_CDS']], errors='coerce')
    df['Pendientes'] = pd.to_numeric(df[MAP_COLS['PENDIENTES_CDS']], errors='coerce')
    df['Tiempos Logistica'] = pd.to_numeric(df[MAP_COLS['TIEMPO_LOG']], errors='coerce')
    df['CDS recibe'] = df[MAP_COLS['CDS_RECIBE']]
    df['CDS entrega'] = df[MAP_COLS['CDS_ENTREGA']]
    df['Remito Date'] = df[MAP_COLS['FACTURA']]
    df['Bultos'] = df[MAP_COLS['BULTOS']]
    
    return df, cmap

def main():
    logo_path = 'Logo Ofar.png'
    last_upd = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if os.path.exists(logo_path): st.image(logo_path, width=150)
    with col_title:
        st.title("Logistics Dashboard - Taco 2026")
        st.markdown(f"<div class='last-update'>🕒 Sincronizado: {last_upd}</div>", unsafe_allow_html=True)

    df, cmap = load_and_process_data()
    
    # NIC Cleaning (Restored)
    def clean_nic_func(val):
        val = str(val).replace(" ", "").strip()
        if val.isdigit() and len(val) > 9: return val[3:-4]
        return val
    df['NIC_CLEAN'] = df.iloc[:, 2].apply(clean_nic_func)

    # Sidebar Tools
    st.sidebar.button("🔄 Actualizar Datos", on_click=st.cache_data.clear)
    if st.sidebar.button("🧹 Limpiar Filtros"):
        st.cache_data.clear()
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["🔍 Buscador", "⚙️ Tiempos operativos", "📍 CDS"])

    # --- TAB 1: BUSCADOR ---
    with tab1:
        st.subheader("Buscador Global")
        sq = st.text_input("Pedido, Cliente o Remito", "")
        if sq:
            # Use original col names for search if needed, but 'Nro de Pedido', 'Cliente', 'Remito' are standard
            mask = df['Nro de Pedido'].astype(str).str.contains(sq, case=False) | \
                   df['Cliente'].astype(str).str.contains(sq, case=False) | \
                   df['Remito'].astype(str).str.contains(sq, case=False)
            if len(sq) > 7: mask |= df['NIC_CLEAN'].astype(str).str.contains(sq)
            res = df[mask].drop_duplicates(subset=['Nro de Pedido', 'Remito'])
            
            for _, r in res.iterrows():
                f_np = r[cmap['NP_ALTA']].strftime('%d/%m/%Y') if pd.notnull(r[cmap['NP_ALTA']]) else 'S/D'
                f_ap = r[cmap['NP_APROB']].strftime('%d/%m/%Y') if pd.notnull(r[cmap['NP_APROB']]) else 'S/D'
                f_fc = r[cmap['FACTURA']].strftime('%d/%m/%Y') if pd.notnull(r[cmap['FACTURA']]) else 'S/D'
                f_dp = r[cmap['DESPACHO']].strftime('%d/%m/%Y') if pd.notnull(r[cmap['DESPACHO']]) else 'S/D'
                
                st.markdown(f"""
                <div class="search-card">
                    <div class="card-header"><h3>{r['Cliente']}</h3></div>
                    <div class="card-subtitle">Pedido: <b>{r['Nro de Pedido']}</b> | Remito: <b>{r['Remito']}</b> | Zona: <b>{r['AMBA/INTERIOR']}</b></div>
                    <div class="timeline-container">
                        <div class="timeline-item">📅 <b>Alta Nota de Pedido:</b> {f_np}</div>
                        <div class="timeline-item">✅ <b>Aprobación Cuentas:</b> {f_ap}</div>
                        <div class="timeline-item">📑 <b>Facturación y Remito:</b> {f_fc}</div>
                        <div class="timeline-item">🚚 <b>Despacho (Logística):</b> {f_dp}</div>
                        {"<div class='timeline-item'>📍 <b>Ingreso CDS:</b> " + r[cmap['CDS_RECIBE']].strftime('%d/%m/%Y') + "</div>" if pd.notnull(r[cmap['CDS_RECIBE']]) else ""}
                        {"<div class='timeline-item'>🏁 <b>Entrega Final CDS:</b> " + str(r['CDS entrega']) + "</div>" if r['AMBA/INTERIOR'] == 'CDS' else ""}
                    </div>
                    <div class="summary-box">⏱️ Despacho: <b>{r['Dias NP/LR']} días</b> | NIC: <b>{r['NIC_CLEAN']}</b></div>
                </div>
                """, unsafe_allow_html=True)

    # --- TAB 2: TIEMPOS OPERATIVOS ---
    with tab2:
        st.subheader("📊 Pendientes de Gestión")
        p_armado = df[df['estado de pedido'] == "Pendiente de armado"]
        p_despacho = df[df['estado de pedido'] == "Pendiente de despacho"]
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Pendiente Armado (Sin Bultos)", len(p_armado))
            with st.expander("Ver detalle Armado"):
                st.dataframe(p_armado[['Nro de Pedido', 'Cliente', 'Remito', 'Remito Date']], use_container_width=True, hide_index=True)
        
        with c2:
            st.metric("Pendiente Despacho (Sin LR)", len(p_despacho))
            with st.expander("Ver detalle Despacho"):
                st.dataframe(p_despacho[['Nro de Pedido', 'Cliente', 'Remito', 'Bultos']], use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📅 Actividad Diaria (Remitido por día)")
        
        # Activity summary based on Column O (Remito Date)
        if pd.notnull(df[cmap['FACTURA']]).any():
            act_df = df.dropna(subset=[cmap['FACTURA']]).copy()
            act_df = act_df[act_df[cmap['FACTURA']].dt.year == 2026]
            
            act_df['Mes'] = act_df[cmap['FACTURA']].dt.strftime('%Y-%m')
            act_df['Fecha_Raw'] = act_df[cmap['FACTURA']].dt.date
            act_df['Fecha_Str'] = act_df[cmap['FACTURA']].dt.strftime('%d/%m/%Y')
            
            sel_month = st.selectbox("Seleccione el Mes para Actividad", sorted(act_df['Mes'].unique(), reverse=True))
            m_data = act_df[act_df['Mes'] == sel_month].copy()
            
            # Aggregate by date using the calculated status for consistency
            summary = m_data.groupby(['Fecha_Raw', 'Fecha_Str']).agg(
                Remitos_diarios=('Nro de Pedido', 'count'),
                Pendiente_armado=('estado de pedido', lambda x: (x == 'Pendiente de armado').sum()),
                Pendiente_despacho=('estado de pedido', lambda x: (x == 'Pendiente de despacho').sum())
            ).reset_index().sort_values('Fecha_Raw', ascending=False)
            
            # Final columns as requested
            summary = summary[['Fecha_Str', 'Remitos_diarios', 'Pendiente_armado', 'Pendiente_despacho']]
            summary.columns = ['Fecha', 'Remitos diarios', 'Pendiente de armado', 'Pendiente de despacho']
            
            st.dataframe(summary, use_container_width=True, hide_index=True)
        else:
            st.info("No hay remitos registrados en 2026 para mostrar actividad.")

        st.markdown("---")
        st.subheader("⏱️ Promedios Mensuales (2026)")
        if pd.notnull(df[cmap['NP_ALTA']]).any():
            df_2026 = df[df[cmap['NP_ALTA']].dt.year == 2026].copy()
            df_t = df_2026.dropna(subset=['Dias NP/LR', cmap['NP_ALTA']]).copy()
            
            if not df_t.empty:
                avg_2026 = df_t['Dias NP/LR'].mean()
                st.metric("Promedio General 2026 (Días NP a LR)", f"{avg_2026:.2f} días")
                df_t['Mes'] = df_t[cmap['NP_ALTA']].dt.strftime('%Y-%m')
                prom_m = df_t.groupby('Mes')['Dias NP/LR'].mean().reset_index()
                tc1, tc2 = st.columns([1, 2])
                with tc1: st.dataframe(prom_m.sort_values('Mes', ascending=False), hide_index=True, use_container_width=True)
                with tc2: st.altair_chart(create_static_bar_chart(prom_m, 'Mes', 'Dias NP/LR'), use_container_width=True)
            else:
                st.info("No hay datos para promedios de despacho 2026.")

        st.markdown("---")
        st.subheader("📦 Tiempos de Logística (Columna AO - Promedios)")
        # Base on FACTURA date for Logistics time activity
        if pd.notnull(df[cmap['FACTURA']]).any():
            df_log = df[df[cmap['FACTURA']].dt.year == 2026].dropna(subset=['Tiempos Logistica', cmap['FACTURA']]).copy()
            if not df_log.empty:
                avg_log_2026 = df_log['Tiempos Logistica'].mean()
                st.metric("Promedio Anual Logística 2026", f"{avg_log_2026:.2f} días")
                df_log['Mes'] = df_log[cmap['FACTURA']].dt.strftime('%Y-%m')
                prom_log = df_log.groupby('Mes')['Tiempos Logistica'].mean().reset_index()
                lc1, lc2 = st.columns([1, 2])
                with lc1: st.dataframe(prom_log.sort_values('Mes', ascending=False), hide_index=True, use_container_width=True)
                with lc2: st.altair_chart(create_static_bar_chart(prom_log, 'Mes', 'Tiempos Logistica'), use_container_width=True)
            else:
                st.info("No hay datos para tiempos de logística 2026.")

    # --- TAB 3: CDS ---
    with tab3:
        st.subheader("🎯 Rendimiento CDS (2026)")
        if pd.notnull(df[cmap['CDS_RECIBE']]).any():
            df_c = df.dropna(subset=['dias de entrega', cmap['CDS_RECIBE']]).copy()
            df_c = df_c[df_c[cmap['CDS_RECIBE']].dt.year == 2026]
            
            if not df_c.empty:
                avg_cds_2026 = df_c['dias de entrega'].mean()
                st.metric("Promedio General CDS 2026", f"{avg_cds_2026:.2f} días")
                
                df_c['Mes'] = df_c[cmap['CDS_RECIBE']].dt.strftime('%Y-%m')
                prom_c = df_c.groupby('Mes')['dias de entrega'].mean().reset_index()
                cc1, cc2 = st.columns([1, 2])
                with cc1: st.dataframe(prom_c.sort_values('Mes', ascending=False), hide_index=True, use_container_width=True)
                with cc2: st.altair_chart(create_static_bar_chart(prom_c, 'Mes', 'dias de entrega'), use_container_width=True)
            else:
                st.info("No hay datos CDS para 2026.")

        st.markdown("---")
        st.subheader("📋 Pendientes CDS (> 10 días)")
        p_cds = df[(df['AMBA/INTERIOR'] == 'CDS') & (df['Pendientes'] > 10)]
        if not p_cds.empty: 
            st.dataframe(p_cds[['Nro de Pedido', 'Cliente', 'Pendientes']].sort_values('Pendientes', ascending=False), use_container_width=True, hide_index=True)
        else: 
            st.info("No hay pendientes críticos.")
        
        st.subheader("🚫 Anulados")
        # Filter for annulled orders in CDS column
        anul = df[df['CDS entrega'].astype(str).str.lower().str.contains('anulado', na=False)]
        if not anul.empty: 
            st.dataframe(anul[['Nro de Pedido', 'Cliente', 'Remito', 'AMBA/INTERIOR']], use_container_width=True, hide_index=True)
        else: 
            st.info("No hay anulados.")

if __name__ == "__main__": main()
