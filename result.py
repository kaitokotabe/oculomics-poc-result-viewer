import io
import os
import datetime
import barcode
from barcode.writer import ImageWriter
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import streamlit as st
from supabase import create_client
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import requests
from io import BytesIO

# --- Supabase 設定 ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]  # RLS用
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# フォント登録
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "ipaexg.ttf")
if not os.path.exists(FONT_PATH):
    raise FileNotFoundError(f"{FONT_PATH} が見つかりません")
pdfmetrics.registerFont(TTFont('IPAexGothic', FONT_PATH))

# --- タイトル ---
st.title("健康チェック結果ページ 🩺")

# --- URLパラメータからUUIDとタイムスタンプ取得 ---
params = st.query_params
uuid = params.get("uuid", [""])
ts = params.get("ts", [None]) # 過去履歴を指定する場合

if not uuid:
    st.warning("アクセス番号（バーコード）を確認できませんでした。")
    st.stop()

uuid_value = uuid

# バーコード生成関数
def generate_barcode(code: str) -> Image.Image:
    CODE128 = barcode.get_barcode_class('code128')
    barcode_obj = CODE128(code, writer=ImageWriter())
    buffer = io.BytesIO()
    barcode_obj.write(buffer)
    buffer.seek(0)
    return Image.open(buffer)

# --- 誕生日確認 ---
st.write("結果をご覧いただくために、ご本人確認をお願いします。")
bday_input = st.date_input(
    "誕生日を入力してください",  
    min_value=datetime.date(1900, 1, 1),
    key="bday_input"
)

if st.button("結果を表示する"):
    if not bday_input:
        st.error("誕生日を入力してください。")
        st.stop()

    # --- RLS対応で直接WHERE条件 ---
    response_q = supabase.table("questionnaires").select("*") \
        .eq("uuid", uuid_value) \
        .eq("bday", bday_input) \
        .execute()
    
    if not response_q.data:
        st.warning("入力された情報と一致する問診がありませんでした。")
        st.stop()
    
    # URLにtsパラメータがあればその時点、なければ最新の問診情報を対象とする
    target_timestamp = ts[0] if ts[0] else response_q.data[0]['timestamp']
    
    # 対象となる問診データを取得
    questionnaire = next((q for q in response_q.data if q['timestamp'] == target_timestamp), None)
    if not questionnaire:
        st.error("指定された履歴が見つかりませんでした。")
        st.stop()
        
    st.success("本人確認ができました ✅ 結果をご確認ください。")

    # --- 過去履歴一覧表示 (元のコードをそのままここに配置) ---
    st.subheader("📅 過去履歴")
    for h in response_q.data: # response_qには全履歴が入っている
        ts_value = h["timestamp"]
        display_date = datetime.datetime.fromisoformat(ts_value).strftime("%Y-%m-%d %H:%M")
        if ts_value == target_timestamp:
            st.markdown(f"- **{display_date} (表示中)**")
        else:
            history_link = f"?uuid={uuid_value}&ts={ts_value}" # uuid_valueを使用
            st.markdown(f"- [{display_date}]({history_link})")

    # 表示中の履歴に対応する結果レコードを取得
    response_res = supabase.table("results").select("*") \
    .eq("questionnaire_uuid", uuid_value) \
    .eq("captured_datetime", target_timestamp) \
    .execute()

    if not response_res.data:
        st.info("この撮影日時のAI解析結果はありません。")
        st.stop()

    # --- 取得した結果を右眼(R)と左眼(L)のデータに振り分ける ---
    right_eye_data = None
    left_eye_data = None
    for record in response_res.data:
        if record.get('eye') == 'R':
            right_eye_data = record
        elif record.get('eye') == 'L':
            left_eye_data = record

    # --- 実年齢の計算 ---
    birth_date = datetime.datetime.fromisoformat(questionnaire['bday']).date()
    today = datetime.date.today()
    real_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

    st.warning("⚠️ この結果はAIによる健康リスク推定です。診断ではありません。こちらは現在東北大学において開発中のアルゴリズムを使用しております。")
    st.caption("気になる点がある場合は、医療機関にご相談ください。")

    # 基本情報表示
    st.subheader("📋 基本情報")
    st.write(f"- 性別: {questionnaire.get('gender', '未登録')}")
    st.write(f"- 誕生日: {questionnaire.get('bday', '未登録')}")
    st.write(f"- 身長: {questionnaire.get('height', '未登録')} cm")
    st.write(f"- 体重: {questionnaire.get('weight', '未登録')} kg")
    st.write(f"- 健康状態: {questionnaire.get('health', '未登録')}")
    if "timestamp" in questionnaire and questionnaire["timestamp"]:
        capture_date = datetime.datetime.fromisoformat(questionnaire["timestamp"]).date()
        st.write(f"- 撮影日: {capture_date}")

    # 画像表示
    def load_image_from_url(url: str) -> Image.Image:
        response = requests.get(url)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))

    # 画像表示（右目・左目）
    st.subheader("👁️ 撮影画像")

    # 横並びにする
    cols = st.columns(2)
    thumb_width = 300
    thumb_height = 300

    # 右目
    if right_eye_data and right_eye_data.get("image_url"):
        right_img = load_image_from_url(right_eye_data["image_url"])
        cols[0].image(right_img, caption="右目", use_container_width=True)
    else:
        cols[0].info("右目の画像はありません。")

    # 左目
    if left_eye_data and left_eye_data.get("image_url"):
        left_img = load_image_from_url(left_eye_data["image_url"])
        cols[1].image(left_img, caption="左目", use_container_width=True)
    else:
        cols[1].info("左目の画像はありません。")
    
    # -------------------------
    # AIによる目の健康評価
    # -------------------------

    # 1. 眼底年齢 (左右別々に表示)
    st.markdown("### 👁️ 眼底年齢")
    st.write(f"**実年齢**: {real_age}歳")

    age_cols = st.columns(2)
    if right_eye_data and right_eye_data.get("fundus_age") is not None:
        age_cols[0].metric(label="右眼の眼底年齢", value=f"{right_eye_data['fundus_age']} 歳",
                         delta=f"{right_eye_data['fundus_age'] - real_age} 歳")
    else:
        age_cols[0].info("右眼の年齢データなし")

    if left_eye_data and left_eye_data.get("fundus_age") is not None:
        age_cols[1].metric(label="左眼の眼底年齢", value=f"{left_eye_data['fundus_age']} 歳",
                         delta=f"{left_eye_data['fundus_age'] - real_age} 歳")
    else:
        age_cols[1].info("左眼の年齢データなし")
    st.caption("Δは実年齢との差")
    st.markdown("---")

    # 2. リスク評価
    def risk_level(score: float) -> str:
        if score < 0.3: return "low"
        elif score < 0.7: return "medium"
        else: return "high"
    def render_risk(label: str, score: float):
        level = risk_level(score)
        st.markdown(f"**{label}**")
        if level == "low": st.success(f"スコア: {score:.2f} (リスク：低 🟢 )")
        elif level == "medium": st.warning(f"スコア: {score:.2f} (リスク：中 🟡 )")
        else: st.error(f"スコア: {score:.2f} (リスク：高 🔴 )")

    # 2a. 緑内障リスク (左右別々に表示)
    st.markdown("### 緑内障リスク")
    st.caption("左右の眼でリスクが異なる場合があるため、個別に表示しています。")
    glaucoma_cols = st.columns(2)
    with glaucoma_cols[0]:
        if right_eye_data and right_eye_data.get("glaucoma_risk") is not None:
            render_risk("右眼", right_eye_data["glaucoma_risk"])
        else:
            st.info("右眼のデータなし")
    with glaucoma_cols[1]:
        if left_eye_data and left_eye_data.get("glaucoma_risk") is not None:
            render_risk("左眼", left_eye_data["glaucoma_risk"])
        else:
            st.info("左眼のデータなし")
    st.markdown("---")

    # 2b. 動脈硬化リスク (平均値を表示)
    st.markdown("### 動脈硬化リスク")
    atherosclerosis_scores = []
    if right_eye_data and right_eye_data.get("atherosclerosis_risk") is not None:
        atherosclerosis_scores.append(right_eye_data["atherosclerosis_risk"])
    if left_eye_data and left_eye_data.get("atherosclerosis_risk") is not None:
        atherosclerosis_scores.append(left_eye_data["atherosclerosis_risk"])

    if atherosclerosis_scores:
        average_score = sum(atherosclerosis_scores) / len(atherosclerosis_scores)
        render_risk("左右の平均", average_score)
    else:
        st.info("動脈硬化リスクのデータがありません。")

# --------------------------------
# PDF生成
# --------------------------------

    # 日本語フォントの登録（既にあれば不要）
    # FONT_PATH = ...
    # pdfmetrics.registerFont(TTFont('IPAexGothic', FONT_PATH))

    def generate_pdf(questionnaire_data, right_eye_data, left_eye_data, real_age):
        """
        問診と左右の眼の結果からPDFレポートを生成する関数（レイアウト＆バグ修正版）
        """
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # Y座標の初期位置
        y_cursor = height - 20 * mm

        # --- ヘッダー ---
        p.setFont('IPAexGothic', 18)
        p.drawString(20 * mm, y_cursor, "健康チェック結果レポート")
        y_cursor -= 6 * mm
        p.setFont('IPAexGothic', 9)
        p.drawString(150 * mm, y_cursor, f"作成日: {datetime.date.today().strftime('%Y-%m-%d')}")
        p.line(20 * mm, y_cursor - 2 * mm, width - 20 * mm, y_cursor - 2 * mm)
        y_cursor -= 5 * mm

        # --- バーコード ---
        uuid_value = questionnaire_data.get('uuid')
        if uuid_value:
            p.drawString(20 * mm, y_cursor, f"受付番号: {uuid_value}")
            y_cursor -= 15 * mm
            try:
                barcode_obj = barcode.get_barcode_class('code128')(uuid_value, writer=ImageWriter())
                barcode_buffer = io.BytesIO()
                barcode_obj.write(barcode_buffer)
                barcode_buffer.seek(0)
                barcode_img = ImageReader(Image.open(barcode_buffer))
                p.drawImage(barcode_img, 20 * mm, y_cursor, width=80*mm, height=12*mm)
                y_cursor -= 5 * mm
                p.setFont('IPAexGothic', 8)
                p.drawString(20 * mm, y_cursor, "次回利用時にこのバーコードをカメラに読ませてください")
            except Exception as e:
                print(f"Barcode generation failed: {e}")
        y_cursor -= 15 * mm

        # --- 基本情報 ---
        p.setFont('IPAexGothic', 12)
        p.drawString(20 * mm, y_cursor, "■ 基本情報")
        y_cursor -= 8 * mm
        p.setFont('IPAexGothic', 10)
        p.drawString(25 * mm, y_cursor, f"性別: {questionnaire_data.get('gender', '-')}")
        p.drawString(70 * mm, y_cursor, f"誕生日: {questionnaire_data.get('bday', '-')}")
        p.drawString(120 * mm, y_cursor, f"実年齢: {real_age} 歳")
        y_cursor -= 15 * mm
        
        # --- 撮影画像 ---
        p.setFont('IPAexGothic', 12)
        p.drawString(20 * mm, y_cursor, "■ 撮影画像")
        img_y_pos = y_cursor - 55 * mm # 画像描画用のY座標を確保
        
        def download_image(url):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                return Image.open(io.BytesIO(response.content))
            except Exception:
                return None

        if right_eye_data and right_eye_data.get("image_url"):
            img = download_image(right_eye_data["image_url"])
            if img:
                p.drawImage(ImageReader(img), 30 * mm, img_y_pos, width=50*mm, height=50*mm, preserveAspectRatio=True, anchor='c')
                p.drawCentredString(55 * mm, img_y_pos - 5*mm, "右眼")
        
        if left_eye_data and left_eye_data.get("image_url"):
            img = download_image(left_eye_data["image_url"])
            if img:
                p.drawImage(ImageReader(img), 115 * mm, img_y_pos, width=50*mm, height=50*mm, preserveAspectRatio=True, anchor='c')
                p.drawCentredString(140 * mm, img_y_pos - 5*mm, "左眼")
        y_cursor -= 70 * mm # 画像とキャプションの分だけカーソルを下に移動

        # --- AIによる健康評価 ---
        # ★★★ このブロック全体がifの外にあることが重要 ★★★
        p.setFont('IPAexGothic', 12)
        p.drawString(20 * mm, y_cursor, "■ AIによる目の健康評価")
        p.line(20 * mm, y_cursor - 2 * mm, width - 20 * mm, y_cursor - 2 * mm)
        y_cursor -= 12 * mm
        
        # 眼底年齢
        p.setFont('IPAexGothic', 11)
        p.drawString(25 * mm, y_cursor, "眼底年齢")
        p.setFont('IPAexGothic', 10)
        if right_eye_data and right_eye_data.get('fundus_age') is not None:
            p.drawString(70 * mm, y_cursor, f"右眼: {right_eye_data.get('fundus_age')} 歳")
        if left_eye_data and left_eye_data.get('fundus_age') is not None:
            p.drawString(120 * mm, y_cursor, f"左眼: {left_eye_data.get('fundus_age')} 歳")
        y_cursor -= 12 * mm

        # 緑内障リスク
        p.setFont('IPAexGothic', 11)
        p.drawString(25 * mm, y_cursor, "緑内障リスク")
        p.setFont('IPAexGothic', 10)
        if right_eye_data and right_eye_data.get('glaucoma_risk') is not None:
            p.drawString(70 * mm, y_cursor, f"右眼: {right_eye_data.get('glaucoma_risk'):.2f}")
        if left_eye_data and left_eye_data.get('glaucoma_risk') is not None:
            p.drawString(120 * mm, y_cursor, f"左眼: {left_eye_data.get('glaucoma_risk'):.2f}")
        y_cursor -= 12 * mm

        # 動脈硬化リスク
        scores = []
        if right_eye_data and right_eye_data.get("atherosclerosis_risk") is not None:
            scores.append(right_eye_data["atherosclerosis_risk"])
        if left_eye_data and left_eye_data.get("atherosclerosis_risk") is not None:
            scores.append(left_eye_data["atherosclerosis_risk"])
        avg_score = (sum(scores) / len(scores)) if scores else -1.0 # 念のためfloatに

        p.setFont('IPAexGothic', 11)
        p.drawString(25 * mm, y_cursor, "動脈硬化リスク")
        p.setFont('IPAexGothic', 10)
        p.drawString(70 * mm, y_cursor, f"左右平均: {average_score:.2f}")
        
        # --- フッター / 注意事項 ---
        p.setFont('IPAexGothic', 9)
        disclaimer = "この結果はAIによる健康リスク推定です。診断ではありません。気になる点がある場合は、医療機関にご相談ください。"
        p.drawString(20 * mm, 30 * mm, disclaimer)
        p.line(20 * mm, 28 * mm, width - 20 * mm, 28 * mm)

        p.save()
        buffer.seek(0)
        return buffer.getvalue()

    st.markdown("---")
    st.subheader("📄 レポートのダウンロード")

    # PDF生成ボタン
    # generate_pdf関数に、取得済みのデータを渡す
    pdf_bytes = generate_pdf(questionnaire, right_eye_data, left_eye_data, real_age)

    st.download_button(
        label="PDFレポートをダウンロード",
        data=pdf_bytes,
        file_name=f"Health_Report_{uuid_value}.pdf",
        mime="application/pdf",
    )
