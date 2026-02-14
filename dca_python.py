import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="DJI DCA Simulator Pro", layout="wide")
st.title("📈 Simulador de Estrategia DCA Avanzada (DJI)")
st.markdown("""
Esta aplicación simula una estrategia de inversión dinámica sobre el Dow Jones (2015-2022). 
Ajusta los parámetros en el panel de la izquierda para ver el impacto en tu ROI.
""")

# --- DATOS HISTÓRICOS (EMBEBIDOS) ---
prices = [
    17165, 18133, 17776, 18030, 18010, 17620, 17690, 16528, 16285, 17663, 17720, 17425, # 2015
    16466, 16517, 17685, 17774, 17787, 17930, 18432, 18400, 18308, 18142, 19124, 19763, # 2016
    19864, 20812, 20663, 20940, 21005, 21350, 21891, 21948, 22405, 23377, 24272, 24719, # 2017
    26149, 25029, 24103, 24163, 24416, 24271, 25415, 25965, 26458, 25116, 25538, 23327, # 2018
    24999, 25916, 25929, 26593, 24815, 26600, 26864, 26403, 26917, 27046, 28051, 28538, # 2019
    28256, 25409, 21917, 24346, 25383, 25813, 26428, 28430, 27782, 26502, 29639, 30606, # 2020
    29983, 30932, 32981, 33875, 34529, 34503, 34935, 35361, 33844, 35820, 34484, 36338  # 2021
]
dates = pd.date_range(start='2015-01-31', periods=len(prices), freq='M')

# --- SIDEBAR: PARÁMETROS ---
st.sidebar.header("⚙️ Parámetros de Inversión")
capital_inicial = st.sidebar.number_input("Capital Inicial ($)", value=50000)
cash_yield = st.sidebar.slider("Rendimiento Efectivo Anual (%)", 0.0, 7.0, 5.0) / 100

st.sidebar.subheader("🚀 Estrategia de Compra")
trigger_caida = st.sidebar.slider("Gatillo de Caída Mensual (%)", 1, 10, 3) / 100
multiplicador = st.sidebar.selectbox("Multiplicador de Compra en Caída", [2, 3, 4], index=1)

st.sidebar.subheader("💰 Gestión de Ganancias")
usa_profit_take = st.sidebar.checkbox("Activar Venta de Beneficios", value=True)
pnl_target = st.sidebar.slider("Objetivo de PnL para Venta (%)", 5, 20, 8) / 100

st.sidebar.subheader("⚖️ Rebalanceo")
ratio_equity = st.sidebar.slider("Ratio Acciones (%)", 50, 100, 80) / 100

# --- LÓGICA DE SIMULACIÓN ---
def run_simulation():
    num_months = len(prices)
    monthly_base = capital_inicial / num_months
    current_cash = capital_inicial
    shares = 0
    invested_basis = 0
    history = []

    for i, price in enumerate(prices):
        # Interés sobre el efectivo
        current_cash *= (1 + cash_yield / 12)
        
        # Retorno mensual para el gatillo
        monthly_ret = (price - prices[i-1]) / prices[i-1] if i > 0 else 0
        
        # 1. Compra DCA
        buy_amount = monthly_base * multiplicador if monthly_ret <= -trigger_caida else monthly_base
        actual_buy = min(buy_amount, current_cash)
        shares += actual_buy / price
        current_cash -= actual_buy
        invested_basis += actual_buy
        
        # 2. Toma de Ganancias (Opcional)
        if usa_profit_take:
            equity_val = shares * price
            if invested_basis > 0 and (equity_val / invested_basis) - 1 > pnl_target:
                surplus = equity_val - (invested_basis * (1 + pnl_target))
                shares_sold = surplus / price
                invested_basis -= shares_sold * (invested_basis / shares)
                shares -= shares_sold
                current_cash += surplus
        
        # 3. Rebalanceo
        equity_val = shares * price
        total_val = current_cash + equity_val
        target_eq_val = total_val * ratio_equity
        adj = target_eq_val - equity_val
        
        if adj > 0: # Compra
            v = min(adj, current_cash)
            shares += v / price
            current_cash -= v
            invested_basis += v
        else: # Venta
            v = abs(adj)
            shares_sold = v / price
            invested_basis -= shares_sold * (invested_basis / shares) if shares > 0 else 0
            shares -= shares_sold
            current_cash += v
            
        history.append({
            "Fecha": dates[i],
            "Precio": price,
            "Total": current_cash + (shares * price),
            "Efectivo": current_cash,
            "Acciones": shares * price,
            "Trigger": monthly_ret <= -trigger_caida
        })
    return pd.DataFrame(history)

df_res = run_simulation()

# --- VISUALIZACIÓN ---
col1, col2, col3 = st.columns(3)
final_val = df_res['Total'].iloc[-1]
roi = ((final_val / capital_inicial) - 1) * 100

col1.metric("Valor Final", f"${final_val:,.2f}")
col2.metric("ROI Total", f"{roi:.2f}%")
col3.metric("Efectivo Final", f"${df_res['Efectivo'].iloc[-1]:,.2f}")

# Gráfica de Crecimiento
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_res['Fecha'], y=df_res['Total'], name="Valor Portafolio", fill='tozeroy'))
fig.add_trace(go.Scatter(x=df_res['Fecha'], y=[capital_inicial]*len(df_res), name="Capital Inicial", line=dict(dash='dash', color='red')))
fig.update_layout(title="Evolución del Patrimonio", xaxis_title="Año", yaxis_title="USD", hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# Gráfica de DJI con Triggers
fig2 = go.Figure()
fig2.add_trace(go.Scatter(x=df_res['Fecha'], y=df_res['Precio'], name="Precio DJI", line=dict(color='grey')))
triggers = df_res[df_res['Trigger']]
fig2.add_trace(go.Scatter(x=triggers['Fecha'], y=triggers['Precio'], mode='markers', name="Gatillo Activado", marker=dict(color='red', size=10)))
fig2.update_layout(title="Puntos de Compra Agresiva (Gatillo)", xaxis_title="Año", yaxis_title="Precio")
st.plotly_chart(fig2, use_container_width=True)

st.write("### Registro de Operaciones")
st.dataframe(df_res)