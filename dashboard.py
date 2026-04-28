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
        df1 = pd.read_csv(HOJA1_URL)
        df2 = pd.read_csv(HOJA2_URL)
    except Exception as e:
        st.error(f"Error conectando a GSheets: {e}")
        st.stop()

    def get_col(df, idx, keywords):
        if idx < len(df.columns):
            col_name = df.columns[idx]
            if any(k.lower() in col_name.lower() for k in keywords): return col_name
        for col in df.columns:
            if any(k.lower() in col.lower() for k in keywords): return col
        return df.columns[idx] if idx < len(df.columns) else None

    # Column Mapping
    C_NIC = get_col(df1, 2, ['NIC'])
    H_NP_ALTA = get_col(df1, 7, ['NP Alta', 'Fecha y hora'])
    L_APROB = get_col(df1, 11, ['NP de aprob', 'final'])
    O_FACTURA = get_col(df1, 14, ['Comprobante', 'Fecha y Hora'])
    R_DESTINO = get_col(df1, 17, ['Destinatario', 'Nombre'])
    S_FECHA = get_col(df1, 18, ['Fecha'])
    AB_DESPACHO = get_col(df1, 27, ['LR Fecha', 'Hora'])

    # 1. NIC Cleaning
    def clean_nic(val):
        val = str(val).replace(" ", "").strip()
        if val.isdigit() and len(val) > 9: return val[3:-4]
        return val
    df1['NIC_CLEAN'] = df1[C_NIC].apply(clean_nic)

    # 2. Hoja2 Lookup
    h2 = df2.iloc[:, [1, 5, 14]].copy()
    h2.columns = ['NIC_H2', 'AK_RECIBE', 'AL_ENTREGA']
    h2['NIC_H2'] = h2['NIC_H2'].astype(str).str.strip()
    df = df1.merge(h2, left_on='NIC_CLEAN', right_on='NIC_H2', how='left')

    # 3. Date Conversion
    for col in [H_NP_ALTA, L_APROB, O_FACTURA, S_FECHA, AB_DESPACHO, 'AK_RECIBE']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')

    # 4. AF: Zone
    def get_zone(val):
        v = str(val).lower()
        if "cruz del sur" in v: return "CDS"
        if any(x in v for x in ["kergaravat", "administracion", "freiria", "rejon"]): return "AMBA"
        return "Interior"
    df['ZONA'] = df[R_DESTINO].apply(get_zone)

    # 5. AG: Status
    def get_status(row):
        if pd.notnull(row[AB_DESPACHO]): return "Despachado"
        if pd.notnull(row[S_FECHA]): return "Pendiente de despacho"
        if pd.notnull(row[O_FACTURA]): return "Pendiente de armado"
        return "S/D"
    df['ESTADO'] = df.apply(get_status, axis=1)

    # 6. Calculations
    df['DIAS_NP_LR'] = (df[AB_DESPACHO] - df[H_NP_ALTA]).dt.days
    df['AL_TEXT'] = df['AL_ENTREGA'].astype(str).str.lower()
    df['AL_DATE'] = pd.to_datetime(df['AL_ENTREGA'], dayfirst=True, errors='coerce')
    df['DIAS_CDS'] = (df['AL_DATE'] - df['AK_RECIBE']).dt.days
    df['DIAS_PENDIENTES_CDS'] = np.where(
        (df['AL_TEXT'].str.contains('pendiente')) & (pd.notnull(df['AK_RECIBE'])),
        (TODAY - df['AK_RECIBE']).dt.days,
        np.nan
    )
    df['TIEMPO_LOGISTICA'] = (df[AB_DESPACHO] - df[O_FACTURA]).dt.days

    # Consistency names
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
    
    return df, {'NP_ALTA': H_NP_ALTA, 'NP_APROB': L_APROB, 'FACTURA': O_FACTURA, 'DESPACHO': AB_DESPACHO}

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
    st.sidebar.button("🔄 Actualizar", on_click=st.cache_data.clear)

    tab1, tab2, tab3 = st.tabs(["🔍 Buscador", "⚙️ Tiempos operativos", "📍 CDS"])

    # --- TAB 1: BUSCADOR ---
    with tab1:
        st.subheader("Buscador Global")
        sq = st.text_input("Pedido, Cliente o Remito", "")
        if sq:
            mask = df['Nro de Pedido'].astype(str).str.endswith(sq) | df['Cliente'].astype(str).str.contains(sq, case=False) | df['Remito'].astype(str).str.contains(sq, case=False)
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
                        {"<div class='timeline-item'>📍 <b>Ingreso CDS:</b> " + r['CDS recibe'].strftime('%d/%m/%Y') + "</div>" if pd.notnull(r['CDS recibe']) else ""}
                        {"<div class='timeline-item'>🏁 <b>Entrega Final CDS:</b> " + str(r['CDS entrega']) + "</div>" if r['AMBA/INTERIOR'] == 'CDS' else ""}
                    </div>
                    <div class="summary-box">⏱️ Despacho: <b>{r['Dias NP/LR']} días</b> | NIC: <b>{r['NIC_CLEAN']}</b></div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("Buscador por Cliente (Promedios)")
        clist = sorted(df['Cliente'].dropna().unique())
        sel_c = st.selectbox("Seleccione un Cliente", [""] + clist)
        if sel_c:
            cdf = df[df['Cliente'] == sel_c]
            c1, c2, c3 = st.columns(3)
            c1.metric("Promedio NP a LR", f"{cdf['Dias NP/LR'].mean():.2f}" if pd.notnull(cdf['Dias NP/LR'].mean()) else "S/D")
            cds_cdf = cdf[cdf['AMBA/INTERIOR'] == 'CDS']
            c2.metric("Promedio CDS", f"{cds_cdf['dias de entrega'].mean():.2f}" if not cds_cdf.empty else "No aplica")
            c3.metric("Total Pedidos", len(cdf))
            st.dataframe(cdf[['Nro de Pedido', 'Remito', 'AMBA/INTERIOR', 'Dias NP/LR', 'dias de entrega']].sort_values('Nro de Pedido', ascending=False), use_container_width=True, hide_index=True)

    # --- TAB 2: TIEMPOS OPERATIVOS ---
    with tab2:
        st.subheader("📊 Pendientes de Gestión")
        sc1, sc2 = st.columns(2)
        sc1.metric("Pendiente Armado", len(df[df['estado de pedido'] == "Pendiente de armado"]))
        sc2.metric("Pendiente Despacho", len(df[df['estado de pedido'] == "Pendiente de despacho"]))
        
        st.markdown("---")
        st.subheader("📅 Actividad Diaria")
        if pd.notnull(df[cmap['FACTURA']]).any():
            piv = df.dropna(subset=[cmap['FACTURA']]).copy()
            piv = piv[piv[cmap['FACTURA']].dt.year == 2026]
            piv['Fecha'] = piv[cmap['FACTURA']].dt.date
            piv['Mes'] = piv[cmap['FACTURA']].dt.strftime('%b').str.lower()
            res_piv = piv.groupby(['Mes', 'Fecha']).agg({'Nro de Pedido': 'count'}).reset_index()
            res_piv.columns = ['Mes', 'Fecha', 'Total']
            st.dataframe(res_piv.sort_values('Fecha', ascending=False), use_container_width=True)

        st.markdown("---")
        st.subheader("⏱️ Promedios Mensuales")
        if pd.notnull(df[cmap['NP_ALTA']]).any():
            df_t = df.dropna(subset=['Dias NP/LR', cmap['NP_ALTA']]).copy()
            df_t['Mes'] = df_t[cmap['NP_ALTA']].dt.strftime('%Y-%m')
            prom_m = df_t.groupby('Mes')['Dias NP/LR'].mean().reset_index()
            tc1, tc2 = st.columns([1, 2])
            with tc1: st.dataframe(prom_m.sort_values('Mes', ascending=False), hide_index=True)
            with tc2: st.altair_chart(create_static_bar_chart(prom_m, 'Mes', 'Dias NP/LR'), use_container_width=True)

    # --- TAB 3: CDS ---
    with tab3:
        st.subheader("🎯 Rendimiento CDS")
        if pd.notnull(df['CDS recibe']).any():
            df_c = df.dropna(subset=['dias de entrega', 'CDS recibe']).copy()
            df_c['Mes'] = df_c['CDS recibe'].dt.strftime('%Y-%m')
            prom_c = df_c.groupby('Mes')['dias de entrega'].mean().reset_index()
            cc1, cc2 = st.columns([1, 2])
            with cc1: st.dataframe(prom_c.sort_values('Mes', ascending=False), hide_index=True)
            with cc2: st.altair_chart(create_static_bar_chart(prom_c, 'Mes', 'dias de entrega'), use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Pendientes CDS (> 10 días)")
        p_cds = df[(df['AMBA/INTERIOR'] == 'CDS') & (df['Pendientes'] > 10)]
        if not p_cds.empty: st.dataframe(p_cds[['Nro de Pedido', 'Cliente', 'Pendientes']].sort_values('Pendientes', ascending=False), use_container_width=True)
        else: st.info("No hay pendientes críticos.")
        
        st.subheader("🚫 Anulados")
        anul = df[df['AL_TEXT'].str.contains('anulado', na=False)]
        if not anul.empty: st.dataframe(anul[['Nro de Pedido', 'Cliente', 'Remito', 'AMBA/INTERIOR']], use_container_width=True)
        else: st.info("No hay anulados.")

if __name__ == "__main__": main()
