import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import altair as alt

# Use dynamic today's date
TODAY = datetime.now()

# Google Sheets URL (Exported as CSV to get computed values)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1ztQKIs8KNf5QZPPDItP9S63JvrmIgCmiQvFLtIKm74k/export?format=csv"

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
[data-testid="stMetricValue"] { color: #58a6ff !important; font-size: 2rem !important; }
[data-testid="stMetricLabel"] { color: #c9d1d9 !important; font-weight: bold !important; }
.stMetric {
    background-color: #161b22;
    padding: 20px;
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
    chart = alt.Chart(data).mark_bar(color='#58a6ff').encode(
        x=alt.X(f'{x_col}:N', title=x_col),
        y=alt.Y(f'{y_col}:Q', title=y_col),
        tooltip=[x_col, y_col]
    ).properties(width='container', height=300).configure_axis(labelColor='#c9d1d9', titleColor='#c9d1d9').configure_view(strokeOpacity=0)
    return chart

@st.cache_data(ttl=600)
def load_data():
    try:
        df = pd.read_csv(SHEET_URL)
    except Exception as e:
        st.warning(f"No se pudo conectar a Google Sheets, intentando carga local... (Error: {e})")
        file_path = 'Libro1.xlsx'
        if os.path.exists(file_path):
            df = pd.read_excel(file_path, sheet_name=0)
        else:
            raise Exception("No se encontró ninguna fuente de datos.")
    
    def find_col(substrings):
        for col in df.columns:
            if all(s.lower() in col.lower() for s in substrings): return col
        return None

    cols_map = {
        'NP_ALTA': find_col(['NP Alta', 'Fecha y hora']),
        'NP_APROB': find_col(['NP de aprob', 'final', 'Fecha y hora']),
        'COMPROBANTE': find_col(['Comprobante', 'Fecha y Hora']),
        'LR_FECHA': find_col(['LR Fecha y Hora']),
        'CDS_RECIBE': find_col(['CDS recibe']),
        'CDS_ENTREGA': find_col(['CDS entrega']),
        'AMBA_INT': find_col(['AMBA', 'INTERIOR']),
        'ESTADO': find_col(['estado de pedido'])
    }

    # Date columns conversion
    for key in ['NP_ALTA', 'NP_APROB', 'COMPROBANTE', 'LR_FECHA', 'CDS_RECIBE']:
        col = cols_map[key]
        if col and col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
    
    # Numeric columns
    numeric_cols = ['dias de entrega', 'Pendientes', 'Dias NP/LR', 'Tiempos Logistica']
    for col in numeric_cols:
        target = find_col([col]) if col not in df.columns else col
        if target and target in df.columns:
            df[target] = pd.to_numeric(df[target], errors='coerce')
    return df, cols_map

def main():
    logo_path = 'Logo Ofar.png'
    last_upd = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    
    col_logo, col_title = st.columns([1, 4])
    with col_logo:
        if os.path.exists(logo_path): st.image(logo_path, width=150)
    with col_title:
        st.title("Dashboard de Logística - Taco 2026")
        st.markdown(f"<div class='last-update'>🕒 Sincronizado con Google Sheets: {last_upd}</div>", unsafe_allow_html=True)

    st.markdown("---")
    try:
        df, cmap = load_data()
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        return

    if st.sidebar.button("🔄 Sincronizar ahora"):
        st.cache_data.clear()
        st.rerun()

    tab1, tab2, tab3 = st.tabs(["🔍 Buscador", "⚙️ Tiempos operativos", "📍 CDS"])

    # --- TAB 1: BUSCADOR ---
    with tab1:
        st.subheader("Buscador Global")
        search_query = st.text_input("Buscar por Pedido, Cliente o Remito", "")
        if search_query:
            sq = search_query.strip()
            mask = (
                df['Nro de Pedido'].astype(str).str.endswith(sq, na=False) |
                df['Cliente'].astype(str).str.contains(sq, case=False, na=False) |
                df['Remito'].astype(str).str.contains(sq, case=False, na=False)
            )
            if len(sq) > 7:
                mask = mask | df['NIC'].astype(str).str.contains(sq, na=False) | df['NIC real'].astype(str).str.contains(sq, na=False)
            
            filtered_df = df[mask].drop_duplicates(subset=['Nro de Pedido', 'Remito'])
            
            if not filtered_df.empty:
                for _, row in filtered_df.iterrows():
                    is_cds = 'CDS' in str(row[cmap['AMBA_INT']]).upper()
                    f_np = row[cmap['NP_ALTA']].strftime('%d/%m/%Y') if cmap['NP_ALTA'] and pd.notnull(row[cmap['NP_ALTA']]) else 'S/D'
                    f_ap = row[cmap['NP_APROB']].strftime('%d/%m/%Y') if cmap['NP_APROB'] and pd.notnull(row[cmap['NP_APROB']]) else 'S/D'
                    f_fc = row[cmap['COMPROBANTE']].strftime('%d/%m/%Y') if cmap['COMPROBANTE'] and pd.notnull(row[cmap['COMPROBANTE']]) else 'S/D'
                    f_dp = row[cmap['LR_FECHA']].strftime('%d/%m/%Y') if cmap['LR_FECHA'] and pd.notnull(row[cmap['LR_FECHA']]) else 'S/D'
                    
                    html_content = f'<div class="search-card">'
                    html_content += f'<div class="card-header"><h3>{row["Cliente"]}</h3></div>'
                    html_content += f'<div class="card-subtitle">Pedido: <b>{row["Nro de Pedido"]}</b> | Remito: <b>{row["Remito"]}</b> | Zona: <b>{row[cmap["AMBA_INT"]]}</b></div>'
                    html_content += f'<div class="timeline-container">'
                    html_content += f'<div class="timeline-item">📅 <b>Alta Nota de Pedido:</b> {f_np}</div>'
                    html_content += f'<div class="timeline-item">✅ <b>Aprobación Cuentas:</b> {f_ap}</div>'
                    html_content += f'<div class="timeline-item">📑 <b>Facturación y Remito:</b> {f_fc}</div>'
                    html_content += f'<div class="timeline-item">🚚 <b>Despacho (Logística):</b> {f_dp}</div>'
                    if is_cds:
                        f_ak = row[cmap['CDS_RECIBE']].strftime('%d/%m/%Y') if cmap['CDS_RECIBE'] and pd.notnull(row[cmap['CDS_RECIBE']]) else 'S/D'
                        f_al = str(row[cmap['CDS_ENTREGA']])
                        html_content += f'<div class="timeline-item">📍 <b>Ingreso CDS:</b> {f_ak}</div>'
                        html_content += f'<div class="timeline-item">🏁 <b>Entrega Final CDS:</b> {f_al}</div>'
                        html_content += f'</div><div class="summary-box">'
                        html_content += f'⏱️ <b>Tiempos:</b> Días Despacho: <b>{row["Dias NP/LR"]}</b> | Días CDS: <b>{row["dias de entrega"]}</b> | NIC: <b>{row["NIC real"]}</b>'
                        html_content += f'</div>'
                    else:
                        html_content += f'</div><div class="summary-box">'
                        html_content += f'⏱️ <b>Tiempos:</b> Días Despacho: <b>{row["Dias NP/LR"]}</b>'
                        html_content += f'</div>'
                    html_content += f'</div>'
                    st.markdown(html_content, unsafe_allow_html=True)
            else:
                st.warning("No se encontraron resultados.")

        st.markdown("---")
        st.subheader("Buscador por Cliente (Tiempos Promedio)")
        client_list = sorted(df['Cliente'].dropna().unique())
        selected_client = st.selectbox("Seleccione un Cliente", [""] + client_list)
        if selected_client:
            c_df = df[df['Cliente'] == selected_client]
            avg_ah = c_df['Dias NP/LR'].mean()
            is_any_cds = c_df[cmap['AMBA_INT']].astype(str).str.contains('CDS', na=False).any()
            cds_c_df = c_df[c_df[cmap['AMBA_INT']].astype(str).str.contains('CDS', na=False)]
            avg_am = cds_c_df['dias de entrega'].mean() if not cds_c_df.empty else np.nan
            val_ah = f"{avg_ah:.2f}" if pd.notnull(avg_ah) else "S/D"
            val_am = "No aplica" if not is_any_cds else (f"{avg_am:.2f}" if pd.notnull(avg_am) else "S/D")
            cc1, cc2, cc3 = st.columns(3)
            with cc1: st.metric("Promedio de NP a LR", val_ah)
            with cc2: st.metric("Promedio CDS", val_am)
            with cc3:
                if pd.notnull(avg_ah):
                    total_val = (avg_ah) + (avg_am if pd.notnull(avg_am) else 0)
                    st.metric("Tiempo Total Promedio", f"{total_val:.2f}")
                else: st.metric("Tiempo Total Promedio", "S/D")
            st.markdown(f"**Listado de pedidos para {selected_client} (Muestra: {len(c_df)} pedidos)**")
            st.dataframe(c_df[['Nro de Pedido', 'Remito', cmap['AMBA_INT'], 'Dias NP/LR', 'dias de entrega']].sort_values('Nro de Pedido', ascending=False), use_container_width=True, hide_index=True)

    # --- TAB 2: TIEMPOS OPERATIVOS ---
    with tab2:
        st.subheader("📊 Pendientes de Armado y Despacho")
        s_col1, s_col2, s_col3 = st.columns([1, 1, 1])
        status_lower = df[cmap['ESTADO']].astype(str).str.strip().str.lower()
        with s_col1:
            st.metric("Pendiente Armado", len(df[status_lower == "pendiente de armado"]))
            if st.button("Ver detalle Armado"): st.session_state.view_detail_op = "pendiente de armado"
        with s_col2:
            st.metric("Pendiente de Despacho", len(df[status_lower == "pendiente de despacho"]))
            if st.button("Ver detalle Despacho"): st.session_state.view_detail_op = "pendiente de despacho"
        with s_col3:
            if st.button("🧹 Limpiar detalles"): st.session_state.view_detail_op = None
        if 'view_detail_op' in st.session_state and st.session_state.view_detail_op:
            st.dataframe(df[status_lower == st.session_state.view_detail_op][['Nro de Pedido', 'Remito', 'Cliente', cmap['AMBA_INT'], 'Dias NP/LR']], use_container_width=True, hide_index=True)
        st.markdown("---")
        st.subheader("📅 Resumen de Actividad (Mensual / Diario)")
        if cmap['COMPROBANTE'] in df.columns:
            df_pivot = df.dropna(subset=[cmap['COMPROBANTE']]).copy()
            df_pivot = df_pivot[(df_pivot[cmap['COMPROBANTE']].dt.year == 2026) & (df_pivot[cmap['COMPROBANTE']] <= TODAY)]
            if not df_pivot.empty:
                df_pivot['Fecha'] = df_pivot[cmap['COMPROBANTE']].dt.date
                df_pivot['Mes'] = df_pivot[cmap['COMPROBANTE']].dt.strftime('%b').str.lower()
                st_l = df_pivot[cmap['ESTADO']].astype(str).str.strip().str.lower()
                df_pivot['Total Remitos'] = 1
                df_pivot['Pendientes Prep'] = (st_l == "pendiente de armado").astype(int)
                df_pivot['Pendientes Envío'] = (st_l == "pendiente de despacho").astype(int)
                pivot_table = df_pivot.groupby(['Mes', 'Fecha']).agg({'Total Remitos': 'sum', 'Pendientes Prep': 'sum', 'Pendientes Envío': 'sum'}).reset_index()
                month_order = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
                pivot_table['MesIdx'] = pivot_table['Mes'].apply(lambda x: month_order.index(x) if x in month_order else 99)
                pivot_table = pivot_table.sort_values(['MesIdx', 'Fecha'], ascending=[False, False])
                sel_m = st.selectbox("Filtrar por Mes", pivot_table['Mes'].unique(), key="sel_m_op")
                m_detail = pivot_table[pivot_table['Mes'] == sel_m][['Fecha', 'Total Remitos', 'Pendientes Prep', 'Pendientes Envío']]
                def style_pending(v): return 'background-color: #ffcad4; color: black;' if v > 0 else ''
                try: styled_df = m_detail.style.map(style_pending, subset=['Pendientes Prep', 'Pendientes Envío'])
                except: styled_df = m_detail.style.applymap(style_pending, subset=['Pendientes Prep', 'Pendientes Envío'])
                st.dataframe(styled_df, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.subheader("⏱️ Tiempos de Despacho (Promedio Mensual)")
        if cmap['NP_ALTA'] and 'Dias NP/LR' in df.columns:
            df_tiempos = df.dropna(subset=[cmap['NP_ALTA'], 'Dias NP/LR']).copy()
            df_tiempos = df_tiempos[(df_tiempos[cmap['NP_ALTA']].dt.year == 2026) & (df_tiempos[cmap['NP_ALTA']] <= TODAY)]
            if not df_tiempos.empty:
                st.metric("Promedio General Despacho 2026 (Días)", f"{df_tiempos['Dias NP/LR'].mean():.2f}")
                df_tiempos['Mes Alta'] = df_tiempos[cmap['NP_ALTA']].dt.strftime('%Y-%m')
                p_mens = df_tiempos.groupby('Mes Alta')['Dias NP/LR'].mean().reset_index()
                p_mens.columns = ['Mes', 'Promedio Días']
                t_c1, t_c2 = st.columns([1, 2])
                with t_c1: st.dataframe(p_mens.sort_values('Mes', ascending=False), use_container_width=True, hide_index=True)
                with t_c2: st.altair_chart(create_static_bar_chart(p_mens, 'Mes', 'Promedio Días'), use_container_width=True)
        st.markdown("---")
        st.subheader("🚛 Tiempo Mensual Logístico")
        if 'Tiempos Logistica' in df.columns and cmap['COMPROBANTE'] in df.columns:
            df_log = df.dropna(subset=['Tiempos Logistica', cmap['COMPROBANTE']]).copy()
            df_log = df_log[df_log[cmap['COMPROBANTE']].dt.year == 2026]
            df_log['Mes'] = df_log[cmap['COMPROBANTE']].dt.strftime('%Y-%m')
            st.metric("Promedio General Logístico 2026 (Días)", f"{df_log['Tiempos Logistica'].mean():.2f}")
            log_avg = df_log.groupby('Mes')['Tiempos Logistica'].mean().reset_index()
            log_avg.columns = ['Mes', 'Promedio Logístico']
            l_c1, l_c2 = st.columns([1, 2])
            with l_c1: st.dataframe(log_avg.sort_values('Mes', ascending=False), use_container_width=True, hide_index=True)
            with l_c2: st.altair_chart(create_static_bar_chart(log_avg, 'Mes', 'Promedio Logístico'), use_container_width=True)

    # --- TAB 3: CDS ---
    with tab3:
        st.subheader("🎯 Tiempos CDS (Promedio Mensual)")
        if cmap['CDS_RECIBE'] and 'dias de entrega' in df.columns:
            df_cds = df.dropna(subset=[cmap['CDS_RECIBE'], 'dias de entrega']).copy()
            df_cds = df_cds[(df_cds[cmap['CDS_RECIBE']].dt.year == 2026) & (df_cds[cmap['CDS_RECIBE']] <= TODAY)]
            if not df_cds.empty:
                df_cds['Mes CDS'] = df_cds[cmap['CDS_RECIBE']].dt.strftime('%Y-%m')
                p_cds = df_cds.groupby('Mes CDS')['dias de entrega'].mean().reset_index()
                p_cds.columns = ['Mes', 'Promedio Días CDS']
                c_c1, c_c2 = st.columns([1, 2])
                with c_c1: st.dataframe(p_cds.sort_values('Mes', ascending=False), use_container_width=True, hide_index=True)
                with c_c2: st.altair_chart(create_static_bar_chart(p_cds, 'Mes', 'Promedio Días CDS'), use_container_width=True)
        st.markdown("---")
        st.subheader("📋 Listado de Pendientes CDS (> 10 días)")
        
        # Super flexible filtering for CDS Pendientes
        cds_m = (df[cmap['AMBA_INT']].astype(str).str.contains('CDS', case=False, na=False)) & \
                (df[cmap['CDS_ENTREGA']].astype(str).str.strip().str.lower().str.contains('pendiente', na=False))
        cds_p = df[cds_m].copy()
        
        if not cds_p.empty:
            cds_p = cds_p[cds_p['Pendientes'] > 10]
            if not cds_p.empty:
                st.dataframe(cds_p[['Nro de Pedido', 'Cliente', 'Remito', 'NIC real', 'Pendientes']].sort_values('Pendientes', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.info("✅ No hay pedidos CDS pendientes con más de 10 días.")
        else:
            st.info("✅ No hay pedidos marcados como 'Pendiente' en CDS.")

        st.markdown("---")
        st.subheader("🚫 Anulados")
        # Super flexible filtering for Anulados
        anul_m = df[cmap['CDS_ENTREGA']].astype(str).str.strip().str.lower().str.contains('anulado', na=False)
        anul_df = df[anul_m].copy()
        
        if not anul_df.empty:
            st.dataframe(anul_df[['Nro de Pedido', 'Cliente', 'Remito', 'NIC real', cmap['AMBA_INT']]], use_container_width=True, hide_index=True)
        else:
            st.info("✅ No hay pedidos marcados como 'Anulado'.")

if __name__ == "__main__": main()
