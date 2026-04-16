#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantShura 系统 - Web 数据看板

基于 Streamlit 的 Web 界面，用于展示和分析交易信号数据。
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="QuantShura - 价格行为学 AI 信号中枢",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
    }
    .signal-bull { color: #22c55e; font-weight: bold; }
    .signal-bear { color: #ef4444; font-weight: bold; }
    .signal-range { color: #64748b; font-weight: bold; }
    .analysis-text {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #3b82f6;
        white-space: pre-wrap;
        font-family: 'Courier New', monospace;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=60)
def load_data():
    try:
        conn = sqlite3.connect("data/quant_shura.db")
        query = """
        SELECT id, timestamp, symbol, close_price, is_trend_bar, is_inside,
               is_outside, llm_direction, raw_analysis, created_at
        FROM trade_signals
        ORDER BY created_at DESC
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['created_at'] = pd.to_datetime(df['created_at'])
            df['is_trend_bar_str'] = df['is_trend_bar'].apply(lambda x: '是' if x else '否')
            df['is_inside_str'] = df['is_inside'].apply(lambda x: '是' if x else '否')
            df['is_outside_str'] = df['is_outside'].apply(lambda x: '是' if x else '否')
            df['signal_color'] = df['llm_direction'].map({
                '多头占优': '#22c55e',
                '空头占优': '#ef4444',
                '震荡平衡': '#64748b'
            }).fillna('#94a3b8')
        return df
    except Exception as e:
        st.error(f"加载数据失败: {e}")
        return pd.DataFrame()


def create_metrics(df):
    if df.empty:
        st.warning("暂无数据，请先运行守护进程生成信号")
        return
    total_signals = len(df)
    bullish_signals = len(df[df['llm_direction'] == '多头占优'])
    bearish_signals = len(df[df['llm_direction'] == '空头占优'])
    range_signals = len(df[df['llm_direction'] == '震荡平衡'])
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="📈 总分析次数", value=f"{total_signals}")
    with col2:
        st.metric(label="🐂 多头信号数", value=f"{bullish_signals}")
    with col3:
        st.metric(label="🐻 空头信号数", value=f"{bearish_signals}")
    with col4:
        st.metric(label="〰️ 震荡/观望数", value=f"{range_signals}")


def create_trend_chart(df):
    if df.empty:
        return
    st.subheader("📊 信号趋势分析")
    df_hourly = df.copy()
    df_hourly['hour'] = df_hourly['timestamp'].dt.floor('H')
    df_hourly_agg = df_hourly.groupby(['hour', 'llm_direction']).size().reset_index(name='count')
    fig = px.bar(
        df_hourly_agg, x='hour', y='count', color='llm_direction',
        color_discrete_map={'多头占优': '#22c55e', '空头占优': '#ef4444', '震荡平衡': '#64748b'},
        title="按小时分布的信号数量"
    )
    fig.update_layout(height=400, showlegend=True, legend_title_text="信号方向")
    st.plotly_chart(fig, use_container_width=True)


def main():
    st.markdown('<h1 class="main-header">📊 QuantShura - 价格行为学 AI 信号中枢</h1>', unsafe_allow_html=True)
    df = load_data()
    if not df.empty:
        create_metrics(df)
        st.divider()
        col1, col2 = st.columns([2, 1])
        with col1:
            create_trend_chart(df)
    else:
        st.info("📭 暂无数据记录，请先运行守护进程生成信号")
    st.divider()
    st.caption("💡 提示: 使用左侧筛选器可以按时间、品种和信号方向进行过滤")
    st.caption("🔗 数据源: data/quant_shura.db | 更新时间: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
