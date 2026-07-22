"""動脈硬化リスクの性別・年代別十分位参照データと相対位置計算。"""

from __future__ import annotations

import plotly.graph_objects as go

PERCENTILE_LABELS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

ATHERO_PERCENTILE_TABLE: dict[tuple[str, int], dict] = {
    ("F", 0): {
        "sample_size": 10,
        "percentiles": [
            5.27423082985479e-8, 5.36785066174161e-8, 1.5917479743166e-7,
            1.85522864626364e-7, 5.44616176512136e-7, 0.00000122498056498443,
            0.0000175526395196357, 0.0000571921282244148, 0.000108282559085637,
            0.000191636942327022, 0.000430564978159964,
        ],
    },
    ("F", 10): {
        "sample_size": 22,
        "percentiles": [
            3.05252605414807e-8, 5.40683956273824e-8, 1.01724288015248e-7,
            1.56382024840696e-7, 1.73908836131886e-7, 2.27286129472759e-7,
            2.59403606150954e-7, 3.71674821053602e-7, 5.92162382417882e-7,
            0.00000175456818283237, 0.00000214730789593887,
        ],
    },
    ("F", 20): {
        "sample_size": 226,
        "percentiles": [
            3.33946807984375e-8, 3.94522402302755e-7, 0.00000193244204638177,
            0.00000285552050627302, 0.00000285552050627302, 0.00000285552050627302,
            0.000003273657284808, 0.000003273657284808, 0.000003273657284808,
            0.000003273657284808, 0.0000151469030242879,
        ],
    },
    ("F", 30): {
        "sample_size": 66,
        "percentiles": [
            6.7457975205798e-8, 2.82710033161493e-7, 3.88152329833247e-7,
            6.0942289792365e-7, 8.91382569534471e-7, 0.00000181067861149131,
            0.00000321748620990547, 0.00000474399803351844, 0.0000109390011857613,
            0.0000446479898528196, 0.000626505236141384,
        ],
    },
    ("F", 40): {
        "sample_size": 123,
        "percentiles": [
            8.69560281557824e-8, 0.00000202781579901057, 0.00000395228753404808,
            0.0000105461154817021, 0.0000151883097714745, 0.0000272341603704263,
            0.0000387034640880302, 0.0000654342817142606, 0.000164236730779522,
            0.000324574665864929, 0.00784159451723099,
        ],
    },
    ("F", 50): {
        "sample_size": 214,
        "percentiles": [
            4.53787748710965e-7, 0.0000105739279206318, 0.0000404072226956487,
            0.0000645905907731503, 0.000130889061256312, 0.000243633527134079,
            0.000429660396184772, 0.000825313210953027, 0.00180656146258116,
            0.00379389501176775, 0.050776232033968,
        ],
    },
    ("F", 60): {
        "sample_size": 72,
        "percentiles": [
            4.46753603000616e-7, 0.0000686315623170231, 0.000191887372056954,
            0.000348009314620867, 0.0006033054436557, 0.00117367302300408,
            0.00197200886905193, 0.00286689377389848, 0.00586564121767879,
            0.0116672731004655, 0.0470789335668087,
        ],
    },
    ("F", 70): {
        "sample_size": 50,
        "percentiles": [
            0.0000176677567651495, 0.000493288895813748, 0.00191951531451195,
            0.00593465361744165, 0.00918953884392977, 0.0145979528315365,
            0.0223013292998075, 0.0291950087994337, 0.0340695098042488,
            0.0531228948384524, 0.20472626388073,
        ],
    },
    ("F", 80): {
        "sample_size": 4,
        "percentiles": [
            0.0000655608964734711, 0.000115448681026464, 0.000165336465579458,
            0.000215224250132451, 0.000942646665498615, 0.00200883639627136,
            0.00307502612704411, 0.00513193109072744, 0.00917026652023197,
            0.0132086019497365, 0.017246937379241,
        ],
    },
    ("M", 0): {
        "sample_size": 10,
        "percentiles": [
            0.00000767074925533962, 0.0000156620229972759, 0.0000203725150640821,
            0.0000890217919732095, 0.000198169110808522, 0.000310466784867458,
            0.000387199915712699, 0.000427006080280989, 0.00294016941916198,
            0.0136389601975679, 0.0205476433038712,
        ],
    },
    ("M", 10): {
        "sample_size": 8,
        "percentiles": [
            0.0000158545390149811, 0.0000233594031669782, 0.0000275110360234976,
            0.0000301510170174879, 0.0000388106276659528, 0.0000587423019169364,
            0.0000797455868450925, 0.0000921558348636608, 0.000107391177152749,
            0.00019632998664747, 0.000382912287022918,
        ],
    },
    ("M", 20): {
        "sample_size": 26,
        "percentiles": [
            0.0000085902784121572, 0.000027112287170894, 0.0000445755285909399,
            0.0000464244421891635, 0.0000639468416920863, 0.0000808594231784809,
            0.000123675214126706, 0.000181095791049302, 0.000248822645517066,
            0.000683665159158409, 0.00252929958514869,
        ],
    },
    ("M", 30): {
        "sample_size": 52,
        "percentiles": [
            0.0000282450600934681, 0.000117119940114208, 0.000141581863863394,
            0.000202971935505047, 0.000370668596588075, 0.000648410408757627,
            0.00100747381802648, 0.00224530703853816, 0.0026987586170435,
            0.00366375830490142, 0.0380264557898045,
        ],
    },
    ("M", 40): {
        "sample_size": 138,
        "percentiles": [
            0.0000275916190730641, 0.000275100462022237, 0.000420331722125411,
            0.00056427763774991, 0.00103040018584579, 0.00177062326110899,
            0.00454714531078935, 0.0102588467299938, 0.014466605708003,
            0.0455833055078983, 0.172762483358383,
        ],
    },
    ("M", 50): {
        "sample_size": 100,
        "percentiles": [
            0.000239879344007932, 0.00248121959157288, 0.00940989293158054,
            0.0188080387189984, 0.0398988157510757, 0.0590052306652069,
            0.0704975351691246, 0.0912197358906269, 0.119091238081455,
            0.16856132298708, 0.350411415100098,
        ],
    },
    ("M", 60): {
        "sample_size": 66,
        "percentiles": [
            0.000627319852355868, 0.00587274180725217, 0.0123626179993153,
            0.037247259169817, 0.0548424758017063, 0.0831214897334576,
            0.10614200681448, 0.142054080963135, 0.188491985201836,
            0.246727682650089, 0.454067319631577,
        ],
    },
    ("M", 70): {
        "sample_size": 26,
        "percentiles": [
            0.00183852110058069, 0.132949516177177, 0.164109885692596,
            0.187556639313698, 0.210817784070969, 0.263728991150856,
            0.304089933633804, 0.388945072889328, 0.418137639760971,
            0.445896744728088, 0.473784178495407,
        ],
    },
    ("M", 80): {
        "sample_size": 2,
        "percentiles": [
            0.375301986932755, 0.391412457823753, 0.407522928714752,
            0.423633399605751, 0.43974387049675, 0.455854341387749,
            0.471964812278748, 0.488075283169746, 0.504185754060745,
            0.520296224951744, 0.536406695842743,
        ],
    },
}

GENDER_LABELS = {"M": "男性", "F": "女性"}


def get_age_group(age: int) -> int:
    """実年齢から年代グループ（10歳刻み、上限80）を返す。"""
    return min((age // 10) * 10, 80)


def lookup_percentiles(gender: str, age_group: int) -> dict | None:
    """性別・年代グループに対応する参照データを返す。見つからなければ None。"""
    return ATHERO_PERCENTILE_TABLE.get((gender, age_group))


def score_to_percentile(score: float, percentiles: list[float]) -> float:
    """リスクスコアを同グループ内の百分位（0–100）に変換する。"""
    if score <= percentiles[0]:
        return 0.0
    if score >= percentiles[-1]:
        return 100.0

    for i in range(len(percentiles) - 1):
        low = percentiles[i]
        high = percentiles[i + 1]
        if low <= score <= high:
            if high == low:
                return float(PERCENTILE_LABELS[i + 1])
            ratio = (score - low) / (high - low)
            p_low = PERCENTILE_LABELS[i]
            p_high = PERCENTILE_LABELS[i + 1]
            return p_low + ratio * (p_high - p_low)

    return 100.0


def format_peer_group_label(gender: str, age_group: int) -> str:
    """表示用の比較グループラベル（例: 50代・男性）。"""
    gender_label = GENDER_LABELS.get(gender, gender)
    return f"{age_group}代・{gender_label}"


def get_relative_risk_label(percentile: float) -> str:
    """百分位から5段階の相対リスクラベルを返す。"""
    p = round(percentile)
    if p <= 20:
        return "低い"
    if p <= 40:
        return "やや低い"
    if p <= 60:
        return "平均的"
    if p <= 80:
        return "やや高い"
    return "高い"


def format_relative_comparison_message(peer_label: str, percentile: float) -> str:
    """同年代・同性との比較を直感的な文章に変換する（Markdown用）。"""
    return format_relative_comparison_plain_text(peer_label, percentile, markdown=True)


def format_relative_comparison_plain_text(
    peer_label: str, percentile: float, markdown: bool = False
) -> str:
    """同年代・同性との比較を直感的な文章に変換する（PDF等のプレーンテキスト用）。"""
    label = get_relative_risk_label(percentile)
    p = round(percentile)

    def emph(text: str) -> str:
        return f"**{text}**" if markdown else text

    if p <= 40:
        lower_pct = 100 - p
        return (
            f"あなたの血管健康リスクは、{emph(peer_label)}の方と比べて {emph(label)} と推定されます。"
            f"（同グループの約 {emph(str(lower_pct))}% の方よりリスクが低い位置です）"
        )
    if p <= 60:
        return (
            f"あなたの血管健康リスクは、{emph(peer_label)}の方と比べて {emph(label)} と推定されます。"
        )
    return (
        f"あなたの血管健康リスクは、{emph(peer_label)}の方と比べて {emph(label)} と推定されます。"
        f"（同グループの約 {emph(str(p))}% の方よりリスクが高い位置です）"
    )


def draw_athero_gauge_pdf(
    canvas,
    x_pt: float,
    y_bottom_pt: float,
    width_pt: float,
    height_pt: float,
    percentile: float,
    font_name: str = "IPAexGothic",
) -> None:
    """PDF用の簡易ゲージを描画する。"""
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    risk_label = get_relative_risk_label(percentile)
    display_value = max(0.0, min(100.0, percentile))

    canvas.setFont(font_name, 11)
    canvas.drawCentredString(
        x_pt + width_pt / 2,
        y_bottom_pt + height_pt + 5 * mm,
        f"同年代・同性と比べて：{risk_label}",
    )

    canvas.setFillColor(colors.HexColor("#d4edda"))
    canvas.rect(x_pt, y_bottom_pt, width_pt * 0.4, height_pt, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#fff3cd"))
    canvas.rect(x_pt + width_pt * 0.4, y_bottom_pt, width_pt * 0.2, height_pt, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#f8d7da"))
    canvas.rect(x_pt + width_pt * 0.6, y_bottom_pt, width_pt * 0.4, height_pt, fill=1, stroke=0)

    canvas.setStrokeColor(colors.grey)
    canvas.setFillColor(colors.black)
    canvas.rect(x_pt, y_bottom_pt, width_pt, height_pt, fill=0, stroke=1)

    marker_x = x_pt + width_pt * (display_value / 100.0)
    canvas.setStrokeColor(colors.HexColor("#333333"))
    canvas.setLineWidth(2)
    canvas.line(marker_x, y_bottom_pt, marker_x, y_bottom_pt + height_pt)

    label_y = y_bottom_pt - 5 * mm
    canvas.setFont(font_name, 8)
    canvas.drawString(x_pt, label_y, "低い")
    canvas.drawCentredString(x_pt + width_pt / 2, label_y, "平均的")
    canvas.drawRightString(x_pt + width_pt, label_y, "高い")


def build_athero_gauge_figure(percentile: float) -> go.Figure:
    """相対リスク位置を示す半円ゲージチャートを生成する。"""
    display_value = round(percentile)
    risk_label = get_relative_risk_label(percentile)

    fig = go.Figure(
        go.Indicator(
            mode="gauge",
            value=display_value,
            title={"text": risk_label, "font": {"size": 32}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "#666", "visible": False},
                "bar": {"color": "#555"},
                "bgcolor": "white",
                "borderwidth": 2,
                "bordercolor": "#ccc",
                "steps": [
                    {"range": [0, 40], "color": "#d4edda"},
                    {"range": [40, 60], "color": "#fff3cd"},
                    {"range": [60, 100], "color": "#f8d7da"},
                ],
                "threshold": {
                    "line": {"color": "#333", "width": 4},
                    "thickness": 0.75,
                    "value": display_value,
                },
            },
        )
    )

    fig.update_layout(
        height=300,
        margin=dict(l=30, r=30, t=60, b=40),
        font={"family": "sans-serif"},
        annotations=[
            dict(
                x=0.12,
                y=-0.08,
                xref="paper",
                yref="paper",
                text="低い",
                showarrow=False,
                font={"size": 12, "color": "#666"},
            ),
            dict(
                x=0.5,
                y=-0.08,
                xref="paper",
                yref="paper",
                text="平均的",
                showarrow=False,
                font={"size": 12, "color": "#666"},
            ),
            dict(
                x=0.88,
                y=-0.08,
                xref="paper",
                yref="paper",
                text="高い",
                showarrow=False,
                font={"size": 12, "color": "#666"},
            ),
            dict(
                x=0.5,
                y=-0.18,
                xref="paper",
                yref="paper",
                text="同年代・同性と比べた位置",
                showarrow=False,
                font={"size": 11, "color": "#999"},
            ),
        ],
    )
    return fig
