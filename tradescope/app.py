"""TradeScope TW–ID — Taiwan–Indonesia trade & currency dashboard.

Run:  streamlit run app.py
"""
from __future__ import annotations

from datetime import date, timedelta

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from core import analysis, charts, costs, fx, news, settings, trade
from core.i18n import LANGS, Translator, currency_name

st.set_page_config(page_title="TradeScope TW–ID", page_icon="📈", layout="wide")

S = settings.load()
if "lang" not in st.session_state:
    st.session_state.lang = S["language"]

RANGES = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365, "2Y": 730}


# ---------------------------------------------------------------- helpers
def show(fig, key: str, filename: str, data: pd.DataFrame | pd.Series | None = None, stretch: bool = True):
    """Render a matplotlib figure with PNG (and optional CSV) download buttons."""
    st.pyplot(fig, width="stretch" if stretch else "content")
    png = charts.to_png(fig)
    plt.close(fig)
    cols = st.columns(3)
    cols[0].download_button(t("download_png"), png, f"{filename}.png", "image/png", key=f"png_{key}")
    if data is not None:
        cols[1].download_button(t("download_csv"), data.to_csv().encode("utf-8-sig"), f"{filename}.csv",
                                "text/csv", key=f"csv_{key}")


def pct(v) -> str | None:
    return None if v is None or pd.isna(v) else f"{v:+.2f}%"


def cur_label(c: str) -> str:
    return f"{c} · {currency_name(c, st.session_state.lang)}"


def sample_notice(is_sample: bool):
    if is_sample:
        st.warning(t("offline_notice"))


def check_alerts(rates: dict) -> list[str]:
    hits = []
    for a in S.get("alerts", []):
        if not a.get("enabled", True):
            continue
        try:
            b, q = a["pair"].upper().split("/")
            now = fx.rate(rates, b, q)
        except (KeyError, ValueError, ZeroDivisionError):
            continue
        v = float(a["value"])
        if (a["condition"] == "above" and now > v) or (a["condition"] == "below" and now < v):
            hits.append(t("alert_hit", pair=a["pair"], now=charts.fmt_num(now),
                          cond=t("cond_" + a["condition"]), value=charts.fmt_num(v)))
    return hits


def news_list(df: pd.DataFrame, limit: int | None = None):
    for _, r in (df.head(limit) if limit else df).iterrows():
        when = r["published"].strftime("%Y-%m-%d %H:%M") if pd.notna(r["published"]) else ""
        st.markdown(f"**[{r['title']}]({r['link']})**  \n"
                    f"<span style='color:#8a8984;font-size:0.85em'>{r['source']} · {when}</span>",
                    unsafe_allow_html=True)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.markdown("### TradeScope **TW–ID**")
    lang = st.selectbox("Language · 語言 · Bahasa", list(LANGS), format_func=LANGS.get,
                        index=list(LANGS).index(st.session_state.lang))
    if lang != st.session_state.lang:
        st.session_state.lang = lang
        S["language"] = lang
        settings.save(S)
        st.rerun()
    T = Translator(st.session_state.lang)
    t = T.t
    PAGES = ["dashboard", "currencies", "trade", "news", "tools", "settings"]
    page = st.radio(t("nav"), PAGES, format_func=lambda p: t("page_" + p), label_visibility="collapsed")
    st.divider()
    if st.button(t("refresh"), width="stretch"):
        st.cache_data.clear()
        st.rerun()
    st.caption(t("sidebar_note"))


# ---------------------------------------------------------------- pages
def page_dashboard():
    d, rates, sample = fx.latest()
    hist, hsample = fx.history(RANGES[S.get("default_range", "3M")])
    base, quote = S["base"], S["quote"]

    st.title(t("page_dashboard"))
    st.caption(t("rates_as_of", date=d))
    sample_notice(sample or hsample)
    for h in check_alerts(rates):
        st.warning(h)

    # KPIs
    kpis = [(base, quote), (quote, base), ("USD", "TWD"), ("USD", "IDR")]
    cols = st.columns(4)
    for col, (b, q) in zip(cols, kpis):
        s = fx.pair(hist, b, q)
        mult = 10000 if (b == "IDR") else 1
        val = fx.rate(rates, b, q) * mult
        label = f"{mult:,} {b} → {q}" if mult > 1 else f"1 {b} → {q}"
        col.metric(label, charts.fmt_num(val), pct(analysis.change_over(s, 30)),
                   help=t("delta_30d"), delta_color="off")

    left, right = st.columns([2, 1], gap="large")
    with left:
        rng = st.radio(t("range"), list(RANGES), index=1, horizontal=True, key="dash_range")
        h, hs = fx.history(RANGES[rng])
        s = fx.pair(h, base, quote)
        fig = charts.line({f"{base}/{quote}": s}, title=t("chart_pair_title", base=base, quote=quote),
                          ylabel=t("units_of", cur=quote), w=7, h=4)
        show(fig, "dash", f"{base}_{quote}_{rng}", s)

    with right:
        st.subheader(t("converter"))
        if "conv_from" not in st.session_state:
            st.session_state.conv_from, st.session_state.conv_to = base, quote

        def swap():
            st.session_state.conv_from, st.session_state.conv_to = st.session_state.conv_to, st.session_state.conv_from

        amount = st.number_input(t("amount"), min_value=0.0, value=1000.0, step=100.0, format="%.2f")
        c1, c2 = st.columns(2)
        f = c1.selectbox(t("from"), fx.CURRENCIES, key="conv_from")
        to = c2.selectbox(t("to"), fx.CURRENCIES, key="conv_to")
        st.button(t("swap"), on_click=swap, width="stretch")
        res = fx.convert(amount, f, to, rates)
        st.markdown(f"<div style='font-size:1.9rem;font-weight:700'>{res:,.2f} {to}</div>", unsafe_allow_html=True)
        st.caption(f"1 {f} = {charts.fmt_num(fx.rate(rates, f, to))} {to} · 1 {to} = "
                   f"{charts.fmt_num(fx.rate(rates, to, f))} {f}")
        quick = [100, 1000, 10000, 100000] if f != "IDR" else [100000, 1000000, 10000000, 100000000]
        st.dataframe(pd.DataFrame({f: [f"{q:,}" for q in quick],
                                   to: [f"{fx.convert(q, f, to, rates):,.2f}" for q in quick]}),
                     hide_index=True, width="stretch")

    st.divider()
    left, right = st.columns([1, 1], gap="large")
    with left:
        df = trade.load_annual()
        last = df.iloc[-1]
        st.subheader(t("trade_snapshot", year=int(last["year"])))
        c = st.columns(3)
        c[0].metric(t("total_trade"), f"${last['total'] / 1000:,.2f} bn", pct(last["total_yoy"]))
        c[1].metric(t("tw_exports"), f"${last['tw_exports_usd_m'] / 1000:,.2f} bn", pct(last["exports_yoy"]))
        c[2].metric(t("tw_imports"), f"${last['tw_imports_usd_m'] / 1000:,.2f} bn", pct(last["imports_yoy"]))
        fig = charts.grouped_bars(df["year"].tolist(), {t("tw_exports"): (df["tw_exports_usd_m"] / 1000).tolist(),
                                                       t("tw_imports"): (df["tw_imports_usd_m"] / 1000).tolist()},
                                  ylabel=t("usd_bn"), h=3.6)
        st.pyplot(fig, width="stretch")
        plt.close(fig)
        st.caption(t("source_boft"))
    with right:
        st.subheader(t("latest_news"))
        ndf, err = news.fetch(st.session_state.lang, 30)
        if err or ndf.empty:
            st.info(t("news_unavailable"))
        else:
            news_list(ndf, 6)


def page_currencies():
    d, rates, sample = fx.latest()
    st.title(t("page_currencies"))
    st.caption(t("rates_as_of", date=d))
    tabs = st.tabs([t("tab_analysis"), t("tab_compare"), t("tab_strength"), t("tab_corr"),
                    t("tab_watchlist"), t("tab_historical")])

    # --- chart & analysis tools
    with tabs[0]:
        c = st.columns([1, 1, 2])
        b = c[0].selectbox(t("base"), fx.CURRENCIES, index=fx.CURRENCIES.index(S["base"]), format_func=cur_label)
        q = c[1].selectbox(t("quote"), fx.CURRENCIES, index=fx.CURRENCIES.index(S["quote"]), format_func=cur_label)
        rng = c[2].radio(t("range"), list(RANGES), index=3, horizontal=True, key="an_range")
        if b == q:
            st.info(t("same_currency"))
            q = "IDR" if b != "IDR" else "TWD"
        h, hs = fx.history(RANGES[rng])
        sample_notice(hs)
        s = fx.pair(h, b, q)

        tc = st.columns(6)
        o_sma7 = tc[0].checkbox(t("sma", n=7))
        o_sma30 = tc[1].checkbox(t("sma", n=30))
        o_pct = tc[2].checkbox(t("as_pct"))
        o_hl = tc[3].checkbox(t("mark_hilo"), value=True)
        o_fc = tc[4].checkbox(t("forecast"))
        o_vol = tc[5].checkbox(t("rolling_vol"))

        step_days = max(1, int(pd.Series(s.index).diff().dt.days.median() or 1))
        view = (s / s.iloc[0] - 1) * 100 if o_pct else s
        series = {f"{b}/{q}": view}
        styles = {}
        if o_sma7:
            n = max(2, round(7 / step_days))
            series[t("sma", n=7)] = analysis.sma(view, n)
            styles[t("sma", n=7)] = {"linestyle": "--", "linewidth": 1.6}
        if o_sma30:
            n = max(2, round(30 / step_days))
            series[t("sma", n=30)] = analysis.sma(view, n)
            styles[t("sma", n=30)] = {"linestyle": "--", "linewidth": 1.6}
        band = None
        if o_fc:
            horizon_days = st.slider(t("forecast_horizon"), 7, 90, 30, 7)
            fc = analysis.holt_forecast(view, max(1, horizon_days // step_days))
            series[t("forecast")] = fc["forecast"]
            styles[t("forecast")] = {"linestyle": ":", "linewidth": 2}
            band = fc
        markers = None
        if o_hl:
            markers = {t("high_low"): view[[view.idxmax(), view.idxmin()]]}
        fig = charts.line(series, title=t("chart_pair_title", base=b, quote=q),
                          ylabel="%" if o_pct else t("units_of", cur=q), styles=styles, markers=markers,
                          band=band, h=4.4)
        show(fig, "analysis", f"{b}_{q}_{rng}_analysis", pd.DataFrame(series))
        if o_fc:
            st.caption(t("forecast_note"))

        m = analysis.summary(s)
        mc = st.columns(6)
        mc[0].metric(t("last"), charts.fmt_num(m["last"]))
        mc[1].metric(t("change"), f"{m['change_pct']:+.2f}%")
        mc[2].metric(t("high"), charts.fmt_num(m["high"]), m["high_date"].strftime("%Y-%m-%d"), delta_color="off")
        mc[3].metric(t("low"), charts.fmt_num(m["low"]), m["low_date"].strftime("%Y-%m-%d"), delta_color="off")
        mc[4].metric(t("average"), charts.fmt_num(m["mean"]))
        mc[5].metric(t("volatility"), f"{m['vol']:.2f}%")

        if o_vol:
            win = max(5, round(30 / step_days))
            rv = analysis.rolling_vol(s, win)
            fig = charts.line({t("rolling_vol"): rv}, title=t("rolling_vol_title", pair=f"{b}/{q}"),
                              ylabel="%", h=3.0)
            show(fig, "vol", f"{b}_{q}_volatility", rv)

    # --- compare (indexed to 100)
    with tabs[1]:
        c = st.columns([3, 1])
        picks = c[0].multiselect(t("compare_pick"), [x for x in fx.CURRENCIES if x != "TWD"],
                                 default=S["watchlist"][:5], max_selections=8, format_func=cur_label)
        rng = c[1].selectbox(t("range"), list(RANGES), index=3, key="cmp_range")
        h, hs = fx.history(RANGES[rng])
        sample_notice(hs)
        if picks:
            idx = {p: (1 / h[p]) / (1 / h[p]).iloc[0] * 100 for p in picks}
            fig = charts.line(idx, title=t("compare_title"), ylabel=t("index_100"), h=4.2)
            show(fig, "cmp", f"compare_{rng}", pd.DataFrame(idx))
            st.caption(t("compare_note"))

    # --- strength heatmap
    with tabs[2]:
        h, hs = fx.history(365)
        sample_notice(hs)
        cur = [x for x in fx.CURRENCIES if x != "TWD"]
        windows = {"1W": 7, "1M": 30, "3M": 90, "6M": 180, "1Y": 365}
        tbl = analysis.strength_table(h, cur, windows)
        tbl.index = [cur_label(c) for c in tbl.index]
        fig = charts.heatmap(tbl, title=t("strength_title"))
        show(fig, "heat", "strength_vs_twd", tbl, stretch=False)
        st.caption(t("strength_note"))

    # --- correlation
    with tabs[3]:
        rng = st.radio(t("range"), list(RANGES), index=3, horizontal=True, key="corr_range")
        h, hs = fx.history(RANGES[rng])
        sample_notice(hs)
        cur = [x for x in S["watchlist"] if x in h.columns and x != "TWD"]
        if len(cur) >= 2:
            cm = analysis.corr_matrix(h, cur)
            fig = charts.heatmap(cm, title=t("corr_title"), vlim=1, fmt="{:+.2f}")
            show(fig, "corr", "correlation", cm, stretch=False)
            st.caption(t("corr_note"))
            c = st.columns(2)
            a = c[0].selectbox("A", cur, index=0, key="corr_a")
            bb = c[1].selectbox("B", cur, index=1, key="corr_b")
            if a != bb:
                step_days = max(1, int(pd.Series(h.index).diff().dt.days.median() or 1))
                rc = analysis.rolling_corr(h[a], h[bb], max(5, round(30 / step_days)))
                fig = charts.line({t("rolling_corr", a=a, b=bb): rc}, title=t("rolling_corr", a=a, b=bb), h=3.0)
                show(fig, "rcorr", f"rolling_corr_{a}_{bb}", rc)
        else:
            st.info(t("need_two"))

    # --- watchlist
    with tabs[4]:
        h, hs = fx.history(35)
        sample_notice(sample or hs)
        rows = []
        for c in S["watchlist"]:
            if c == "TWD" or c not in rates:
                continue
            val_twd = 1 / h[c]
            rows.append({t("currency"): cur_label(c),
                         t("per_twd"): charts.fmt_num(rates[c]),
                         t("in_twd"): charts.fmt_num(1 / rates[c]),
                         t("chg_1w"): pct(analysis.change_over(val_twd, 7)),
                         t("chg_1m"): pct(analysis.change_over(val_twd, 30))})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption(t("watchlist_note"))

    # --- historical conversion
    with tabs[5]:
        c = st.columns(4)
        dd = c[0].date_input(t("on_date"), value=date.today() - timedelta(days=365),
                             min_value=fx.EARLIEST, max_value=date.today())
        amt = c[1].number_input(t("amount"), min_value=0.0, value=1000.0, key="hist_amt")
        f = c[2].selectbox(t("from"), fx.CURRENCIES, index=0, key="hist_from")
        to = c[3].selectbox(t("to"), fx.CURRENCIES, index=1, key="hist_to")
        past = fx.on_date(dd)
        if past is None:
            st.info(t("historical_unavailable"))
        else:
            then = fx.convert(amt, f, to, past)
            now = fx.convert(amt, f, to, rates)
            m = st.columns(3)
            m[0].metric(t("then", date=dd.isoformat()), f"{then:,.2f} {to}")
            m[1].metric(t("today"), f"{now:,.2f} {to}")
            m[2].metric(t("difference"), f"{now - then:+,.2f} {to}", pct((now / then - 1) * 100))


def page_trade():
    st.title(t("page_trade"))
    tabs = st.tabs([t("tab_overview"), t("tab_products"), t("tab_hs"), t("tab_edit")])
    df = trade.load_annual()

    with tabs[0]:
        last = df.iloc[-1]
        c = st.columns(4)
        c[0].metric(t("total_trade") + f" {int(last['year'])}", f"${last['total'] / 1000:,.2f} bn", pct(last["total_yoy"]))
        c[1].metric(t("tw_exports"), f"${last['tw_exports_usd_m'] / 1000:,.2f} bn", pct(last["exports_yoy"]))
        c[2].metric(t("tw_imports"), f"${last['tw_imports_usd_m'] / 1000:,.2f} bn", pct(last["imports_yoy"]))
        c[3].metric(t("balance"), f"{'-' if last['balance'] < 0 else ''}${abs(last['balance']) / 1000:,.2f} bn")
        fig = charts.grouped_bars(df["year"].tolist(), {t("tw_exports"): (df["tw_exports_usd_m"] / 1000).tolist(),
                                                       t("tw_imports"): (df["tw_imports_usd_m"] / 1000).tolist()},
                                  title=t("annual_title"), ylabel=t("usd_bn"))
        show(fig, "annual", "tw_id_annual_trade", df.set_index("year"))
        fig = charts.signed_bars(df["year"].tolist(), df["balance"].tolist(), title=t("balance_title"),
                                 ylabel=t("usd_m"))
        show(fig, "bal", "tw_id_balance")

        tbl = df[["year", "tw_exports_usd_m", "tw_imports_usd_m", "total", "balance", "total_yoy"]].copy()
        tbl.columns = [t("year"), t("tw_exports") + " (US$ m)", t("tw_imports") + " (US$ m)",
                       t("total_trade") + " (US$ m)", t("balance") + " (US$ m)", t("total_yoy")]
        st.dataframe(tbl.style.format({tbl.columns[-1]: "{:+.1f}%"}, na_rep="—", thousands=","),
                     hide_index=True, width="stretch")

        c1, c2 = st.columns(2)
        c1.markdown(f"**{t('main_exports')}**\n\n" + "\n".join(f"- {t(k)}" for k in trade.MAIN_EXPORTS))
        c2.markdown(f"**{t('main_imports')}**\n\n" + "\n".join(f"- {t(k)}" for k in trade.MAIN_IMPORTS))
        st.caption(t("source_boft"))

    with tabs[1]:
        st.caption(t("comtrade_note"))
        c = st.columns([1, 2, 1])
        year = c[0].selectbox(t("year"), list(range(date.today().year - 1, 2014, -1)), index=1)
        flow = c[1].radio(t("flow"), ["M", "X"], format_func=lambda f: t("flow_" + f), horizontal=True)
        top_n = c[2].slider(t("top_n"), 5, 25, 15)
        if st.button(t("fetch_comtrade"), type="primary"):
            st.session_state["ct_query"] = (year, flow)
        if "ct_query" in st.session_state:
            y, fl = st.session_state["ct_query"]
            with st.spinner(t("loading")):
                cdf, err = trade.comtrade(y, fl)
            if err:
                st.error(t("comtrade_error", err=err))
            elif cdf.empty:
                st.info(t("no_data"))
            else:
                top = cdf.head(top_n)
                labels = [f"{r.cmdCode} {str(r.cmdDesc)[:38]}" for r in top.itertuples()]
                fig = charts.hbar(labels, (top["primaryValue"] / 1e6).tolist(),
                                  title=t("products_title", flow=t("flow_" + fl), year=y), xlabel=t("usd_m"),
                                  color=charts.PALETTE[0] if fl == "M" else charts.PALETTE[1])
                show(fig, "prod", f"hs2_{fl}_{y}", cdf)

    with tabs[2]:
        st.caption(t("hs_help"))
        c = st.columns([1, 1, 1])
        code = c[0].text_input(t("hs_code"), "8542")
        year = c[1].selectbox(t("year"), list(range(date.today().year - 1, 2014, -1)), index=1, key="hs_year")
        c[2].write("")
        go = c[2].button(t("search"), type="primary")
        if go and code.strip().isdigit():
            res = {}
            for fl in ("M", "X"):
                cdf, err = trade.comtrade(year, fl, code.strip())
                res[fl] = (cdf, err)
            m = st.columns(2)
            for col, fl in zip(m, ("M", "X")):
                cdf, err = res[fl]
                if err:
                    col.error(t("comtrade_error", err=err))
                elif cdf.empty:
                    col.metric(t("flow_" + fl), "—")
                else:
                    col.metric(t("flow_" + fl), f"US$ {cdf['primaryValue'].sum() / 1e6:,.2f} m")
                    col.caption(str(cdf.iloc[0]["cmdDesc"]))

    with tabs[3]:
        st.caption(t("edit_help"))
        raw = pd.read_csv(trade.ANNUAL_CSV)
        edited = st.data_editor(raw, num_rows="dynamic", width="stretch", hide_index=True)
        if st.button(t("save"), type="primary"):
            trade.save_annual(edited)
            st.success(t("saved"))
            st.rerun()


def page_news():
    st.title(t("page_news"))
    c = st.columns([1, 1, 2])
    langs = c[0].multiselect(t("news_lang"), list(LANGS), default=[st.session_state.lang], format_func=LANGS.get)
    days = c[1].selectbox(t("timeframe"), [7, 30, 90], index=1, format_func=lambda d: t("last_days", n=d))
    topic = c[2].selectbox(t("topic"), [None] + list(news.TOPICS),
                           format_func=lambda k: t("topic_all") if k is None else t(k))
    kw = st.text_input(t("keyword_filter"), placeholder=t("keyword_placeholder"))

    frames, errors = [], []
    with st.spinner(t("loading")):
        for lg in langs:
            ndf, err = news.fetch(lg, days, topic)
            if err:
                errors.append(err)
            else:
                frames.append(ndf)
    if not frames or all(f.empty for f in frames):
        st.info(t("news_unavailable"))
        return
    df = pd.concat(frames).sort_values("published", ascending=False)
    if kw:
        df = df[df["title"].str.contains(kw, case=False, na=False)]
    st.caption(t("news_count", n=len(df)) + " · Google News")

    left, right = st.columns([3, 1], gap="large")
    with left:
        news_list(df, 60)
    with right:
        st.markdown(f"**{t('top_sources')}**")
        st.dataframe(df["source"].value_counts().head(10).rename(t("articles")), width="stretch")
        daily = df.set_index("published").resample("D").size()
        if len(daily) > 1:
            fig, ax = charts.fig_ax(w=4, h=2.4)
            ax.bar(daily.index, daily.values, color=charts.PALETTE[0], width=0.8)
            charts._date_axis(ax)
            ax.set_title(t("articles_per_day"), fontsize=10)
            fig.tight_layout()
            st.pyplot(fig, width="stretch")
            plt.close(fig)
        st.download_button(t("download_csv"), df.to_csv(index=False).encode("utf-8-sig"), "tw_id_news.csv")


def page_tools():
    st.title(t("page_tools"))
    tabs = st.tabs([t("tab_landed"), t("tab_incoterms")])
    d, rates, sample = fx.latest()

    with tabs[0]:
        sample_notice(sample)
        direction = st.radio(t("direction"), ["tw_to_id", "id_to_tw"], format_func=lambda x: t(x), horizontal=True)
        dflt = costs.DEFAULTS[direction]
        dest_cur = "IDR" if direction == "tw_to_id" else "TWD"
        c = st.columns(3)
        cur = c[0].selectbox(t("input_currency"), ["TWD", "IDR", "USD"],
                             index=0 if direction == "tw_to_id" else 1)
        goods = c[1].number_input(t("goods_value"), min_value=0.0, value=500000.0 if cur == "TWD" else 250000000.0 if cur == "IDR" else 15000.0)
        qty = c[2].number_input(t("quantity"), min_value=1, value=1000)
        c = st.columns(3)
        freight = c[0].number_input(t("freight"), min_value=0.0, value=goods * 0.06)
        ins = c[1].number_input(t("insurance_pct"), min_value=0.0, value=0.5, step=0.1)
        other = c[2].number_input(t("other_fees"), min_value=0.0, value=goods * 0.02)
        c = st.columns(3)
        duty = c[0].number_input(t("duty_pct"), min_value=0.0, value=dflt["duty"], step=0.5, help=t("duty_help"))
        vat = c[1].number_input(t("vat_pct"), min_value=0.0, value=dflt["vat"], step=0.5)
        it = c[2].number_input(t("income_tax_pct"), min_value=0.0, value=dflt["income_tax"], step=0.5,
                               help=t("income_tax_help"))
        r = costs.landed_cost(goods, freight, ins, duty, vat, it, other)
        conv = fx.rate(rates, cur, dest_cur)

        m = st.columns(4)
        m[0].metric("CIF", f"{r['cif']:,.0f} {cur}")
        m[1].metric(t("landed_total"), f"{r['total']:,.0f} {cur}")
        m[2].metric(t("landed_total") + f" ({dest_cur})", f"{r['total'] * conv:,.0f}")
        m[3].metric(t("per_unit") + f" ({dest_cur})", f"{r['total'] * conv / qty:,.2f}")
        parts = {t("goods"): r["goods"], t("freight_short"): r["freight"], t("insurance"): r["insurance"],
                 t("duty"): r["duty"], t("vat"): r["vat"], t("income_tax"): r["income_tax"],
                 t("other_fees_short"): r["other_fees"]}
        fig = charts.cost_breakdown(parts, title=f"{t('breakdown')} ({cur})")
        show(fig, "landed", "landed_cost")
        tbl = pd.DataFrame({t("item"): list(parts) + [t("landed_total")],
                            cur: [f"{v:,.2f}" for v in parts.values()] + [f"{r['total']:,.2f}"],
                            dest_cur: [f"{v * conv:,.2f}" for v in parts.values()] + [f"{r['total'] * conv:,.2f}"]})
        st.dataframe(tbl, hide_index=True, width="stretch")
        st.caption(t("tax_note"))

    with tabs[1]:
        rows = [{"Incoterm": k, t("name"): n, t("mode"): t("mode_" + mode),
                 t("seller_freight"): "✓" if fr else "—", t("seller_insurance"): "✓" if ins else "—",
                 t("risk_transfer"): t(rk)} for k, n, mode, fr, ins, rk in costs.INCOTERMS]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.caption(t("incoterms_note"))


def page_settings():
    st.title(t("page_settings"))
    with st.form("settings"):
        c = st.columns(3)
        base = c[0].selectbox(t("default_base"), fx.CURRENCIES, index=fx.CURRENCIES.index(S["base"]), format_func=cur_label)
        quote = c[1].selectbox(t("default_quote"), fx.CURRENCIES, index=fx.CURRENCIES.index(S["quote"]), format_func=cur_label)
        rng = c[2].selectbox(t("default_range"), list(RANGES), index=list(RANGES).index(S.get("default_range", "3M")))
        wl = st.multiselect(t("watchlist"), [x for x in fx.CURRENCIES if x != "TWD"], default=S["watchlist"],
                            format_func=cur_label)
        st.markdown(f"**{t('alerts')}**")
        st.caption(t("alerts_help"))
        adf = pd.DataFrame(S.get("alerts", []), columns=["pair", "condition", "value", "enabled"])
        adf = st.data_editor(adf, num_rows="dynamic", width="stretch", hide_index=True,
                             column_config={
                                 "pair": st.column_config.TextColumn(t("pair"), help="TWD/IDR"),
                                 "condition": st.column_config.SelectboxColumn(t("condition"), options=["above", "below"]),
                                 "value": st.column_config.NumberColumn(t("value")),
                                 "enabled": st.column_config.CheckboxColumn(t("enabled"), default=True)})
        if st.form_submit_button(t("save"), type="primary"):
            S.update({"base": base, "quote": quote, "default_range": rng, "watchlist": wl,
                      "alerts": adf.dropna(subset=["pair", "value"]).to_dict("records")})
            settings.save(S)
            st.success(t("saved"))

    st.divider()
    st.markdown(f"**{t('data_sources')}**")
    st.markdown(t("sources_md"))


{"dashboard": page_dashboard, "currencies": page_currencies, "trade": page_trade,
 "news": page_news, "tools": page_tools, "settings": page_settings}[page]()
