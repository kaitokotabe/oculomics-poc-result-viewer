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
    response = supabase.table("questionnaires").select("*") \
        .eq("uuid", uuid_value) \
        .eq("bday", bday_input) \
        .execute()

    if response.data:
        data = response.data[0]
        st.success("本人確認ができました ✅ 結果をご確認ください。")

        # --- 過去履歴一覧表示 ---
        history_response = supabase.table("questionnaires").select("timestamp") \
            .eq("uuid", uuid).eq("bday", bday_input).order("timestamp", desc=True).execute()
        
        if history_response.data:
            st.subheader("📅 過去履歴")
            for h in history_response.data:
                ts_value = h["timestamp"]
                display_date = datetime.datetime.fromisoformat(ts_value).strftime("%Y-%m-%d")
                if ts_value == data["timestamp"]:
                    st.markdown(f"- **{display_date} (表示中)**")
                else:
                    # 履歴リンク
                    history_link = f"?uuid={uuid}&ts={ts_value}"
                    st.markdown(f"- [{display_date}]({history_link})")

        # 実年齢計算
        birth_date = datetime.datetime.fromisoformat(data['bday']).date()
        today = datetime.date.today()
        real_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        st.warning("⚠️ この結果はAIによる健康リスク推定です。診断ではありません。こちらは現在東北大学において開発中のアルゴリズムを使用しております。")
        st.caption("気になる点がある場合は、医療機関にご相談ください。")

        # 基本情報表示
        st.subheader("📋 基本情報")
        st.write(f"- 性別: {data.get('gender', '未登録')}")
        st.write(f"- 誕生日: {data.get('bday', '未登録')}")
        st.write(f"- 身長: {data.get('height', '未登録')} cm")
        st.write(f"- 体重: {data.get('weight', '未登録')} kg")
        st.write(f"- 健康状態: {data.get('health', '未登録')}")
        if "timestamp" in data and data["timestamp"]:
            capture_date = datetime.datetime.fromisoformat(data["timestamp"]).date()
            st.write(f"- 撮影日: {capture_date}")

        def load_image_from_url(url: str) -> Image.Image:
            response = requests.get(url)
            response.raise_for_status()
            return Image.open(BytesIO(response.content))

        # 画像表示（右目・左目）
        st.subheader("👁️ 撮影画像")
        right_img_url = data.get("image_url_right")
        left_img_url = data.get("image_url_left")

        # 横並びにする
        cols = st.columns(2)

        thumb_width = 300
        thumb_height = 300

        # 右目
        if right_img_url:
            right_img = load_image_from_url(right_img_url)
            right_img.thumbnail((thumb_width, thumb_height))
            cols[0].image(right_img, caption="右目", use_container_width=False)
        else:
            cols[0].info("右目の画像は未撮影です。")

        # 左目
        if left_img_url:
            left_img = load_image_from_url(left_img_url)
            left_img.thumbnail((thumb_width, thumb_height))
            cols[1].image(left_img, caption="左目", use_container_width=False)
        else:
            cols[1].info("左目の画像は未撮影です。")
        
        # -------------------------
        # AIによる目の健康評価
        # -------------------------
        # リスク判定関数
        def risk_level(score: float) -> str:
            if score < 0.3:
                return "low"
            elif score < 0.7:
                return "medium"
            else:
                return "high"
        
        st.subheader("🔎 AIによる目の健康評価")

        # result を JSON として読み込む
        result_raw = data.get("result")
        result = {}
        if isinstance(result_raw, str):  
            try:
                result = json.loads(result_raw)  # JSON文字列 → dict
            except json.JSONDecodeError:
                st.error("結果データを読み込めませんでした（JSON形式が不正です）")
                result = {}
        else:
            result = result_raw or {}

        fundus_age = result.get("fundus_age")
        glaucoma_score = result.get("glaucoma_risk")
        atherosclerosis_score = result.get("atherosclerosis_risk")

        if not result:
            st.info("⚡ 現在、AIによる解析中です。")
        else:

            if fundus_age is not None:
                diff = fundus_age - real_age
                st.markdown("### 👁️ 眼底年齢")
                st.write(f"実年齢: {real_age}歳")
                st.write(f"眼底年齢: {fundus_age}歳")
                if diff <= 0:
                    st.success("目の健康状態は年齢相応か、それ以上に良好です 🎉")
                elif diff <= 5:
                    st.warning(f"実年齢より {diff} 歳ほど高めです。生活習慣の見直しをおすすめします。")
                else:
                    st.error(f"実年齢より {diff} 歳以上高めです。定期的なチェックを強くおすすめします。")

            # リスク評価関数
            def render_risk(label: str, score: float):
                if score is None:
                    st.info(f"{label}: データ未取得")
                    return

                level = risk_level(score)
                st.markdown(f"### {label}")
                st.write(f"スコア: {score:.2f}")
                if level == "low":
                    st.success("リスク：低 🟢 安心できる状態です。")
                elif level == "medium":
                    st.warning("リスク：中 🟡 健康に気をつけて生活習慣を見直しましょう。")
                else:
                    st.error("リスク：高 🔴 気になる場合は専門家に相談すると安心です。")

            # 各リスクの表示
            if glaucoma_score is not None:
                render_risk("緑内障リスク", glaucoma_score)
            if atherosclerosis_score is not None:
                render_risk("動脈硬化リスク", atherosclerosis_score)

        # -------------------------
        # PDF生成
        # -------------------------
        def generate_pdf(data, uuid, real_age):
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            y = height - 40

            # タイトル
            c.setFont("IPAexGothic", 18)
            c.drawCentredString(width/2, y, "AIによる目の健康評価 結果")
            y -= 40

            # result JSONを取り出す
            result_raw = data.get("result")
            result = {}
            if isinstance(result_raw, str):
                import json
                try:
                    result = json.loads(result_raw)
                except json.JSONDecodeError:
                    result = {}
            elif isinstance(result_raw, dict):
                result = result_raw

            fundus_age = result.get("fundus_age")
            glaucoma_score = result.get("glaucoma_risk")
            atherosclerosis_score = result.get("atherosclerosis_risk")

            # -------------------------
            # バーコード生成（メモリ上）
            # -------------------------
            CODE128 = barcode.get_barcode_class('code128')
            barcode_obj = CODE128(uuid, writer=ImageWriter())
            barcode_buffer = io.BytesIO()
            barcode_obj.write(barcode_buffer)
            barcode_buffer.seek(0)
            barcode_img = Image.open(barcode_buffer)
            img_reader = ImageReader(barcode_img)

            # PDFに描画
            barcode_width = 80 * mm
            barcode_height = 20 * mm
            c.drawImage(img_reader, (width - barcode_width)/2, y - barcode_height, width=barcode_width, height=barcode_height)
            y -= barcode_height + 10
            c.setFont("IPAexGothic", 10)
            c.drawCentredString(width/2, y, "次回利用時にはこのバーコードをカメラに読ませてください")
            y -= 30

            # 基本情報
            c.setFont("IPAexGothic", 14)
            c.drawString(20, y, "基本情報")
            y -= 20
            c.setFont("IPAexGothic", 14)
            c.drawString(30, y, f"性別: {data.get('gender', '未登録')}")
            y -= 16
            c.setFont("IPAexGothic", 14)
            c.drawString(30, y, f"誕生日: {data.get('bday', '未登録')}")
            y -= 16
            if "timestamp" in data and data["timestamp"]:
                capture_date = data["timestamp"][:10]
                c.setFont("IPAexGothic", 14)
                c.drawString(30, y, f"撮影日: {capture_date}")
                y -= 16
            y -= 10

            # PDF内のサムネイル描画部分
            c.setFont("IPAexGothic", 14)
            c.drawString(20, y, "撮影画像")
            y -= 20
            thumb_height = 60*mm
            thumb_width = 60*mm

            def load_image_from_url(url: str) -> Image.Image:
                response = requests.get(url)
                response.raise_for_status()
                return Image.open(BytesIO(response.content))

            right_img_url = data.get("image_url_right")
            left_img_url = data.get("image_url_left")

            # 左右に並べる x 座標
            x_left = 20
            x_right = x_left + thumb_width + 20  # 左の横に少し余白

            if right_img_url:
                right_img = load_image_from_url(right_img_url)
                c.drawImage(ImageReader(right_img), x_right, y - thumb_height, width=thumb_width, height=thumb_height)
                c.drawString(x_right, y - thumb_height - 12, "右目")

            if left_img_url:
                left_img = load_image_from_url(left_img_url)
                c.drawImage(ImageReader(left_img), x_left, y - thumb_height, width=thumb_width, height=thumb_height)
                c.drawString(x_left, y - thumb_height - 12, "左目")

            y -= thumb_height + 30

            # AI評価
            c.setFont("IPAexGothic", 14)
            c.drawString(20, y, "🔎 AIによる目の健康評価")
            y -= 20
            c.setFont("IPAexGothic", 12)

            if fundus_age is not None:
                diff = fundus_age - real_age
                c.setFont("IPAexGothic", 14)
                c.drawString(30, y, f"実年齢: {real_age}歳")
                y -= 16
                c.setFont("IPAexGothic", 14)
                c.drawString(30, y, f"眼底年齢: {fundus_age}歳")
                y -= 16
                if diff <= 0:
                    c.setFont("IPAexGothic", 14)
                    c.drawString(30, y, "目の健康状態は年齢相応か、それ以上に良好です")
                elif diff <= 5:
                    c.setFont("IPAexGothic", 14)
                    c.drawString(30, y, f"実年齢より {diff} 歳ほど高めです。生活習慣の見直しをおすすめします。")
                else:
                    c.setFont("IPAexGothic", 14)
                    c.drawString(30, y, f"実年齢より {diff} 歳以上高めです。定期的なチェックを強くおすすめします。")
                y -= 20

            # リスク評価
            def score_to_level(score: float) -> str:
                if score < 0.3:
                    return "低"
                elif score < 0.7:
                    return "中"
                else:
                    return "高"

            # リスクをPDFに描画
            def render_risk_pdf(label, score, y_pos):
                if score is None:
                    return y_pos
                level = score_to_level(score)
                c.setFont("IPAexGothic", 14)
                c.drawString(30, y_pos, f"{label}: {score:.2f} （{level}）")
                y_pos -= 16

                if level == "低":
                    c.drawString(35, y_pos, "安心できる状態です")
                elif level == "中":
                    c.drawString(35, y_pos, "健康に気をつけて生活習慣を見直しましょう")
                elif level == "高":
                    c.drawString(35, y_pos, "気になる場合は専門家に相談すると安心です")
                return y_pos - 20

            if glaucoma_score is not None:
                y = render_risk_pdf("緑内障リスク", glaucoma_score, y)
            if atherosclerosis_score is not None:
                y = render_risk_pdf("動脈硬化リスク", atherosclerosis_score, y)

            # 注意書き
            c.setFont("IPAexGothic", 10)
            c.drawString(20, y, "注：この結果はAIによる健康リスク推定です。診断ではありません。")
            y -= 14
            c.setFont("IPAexGothic", 10)
            c.drawString(20, y, "気になる点がある場合は、必ず医療機関にご相談ください。")

            c.save()
            buffer.seek(0)
            return buffer

        pdf_buffer = generate_pdf(data, uuid, real_age)
        st.download_button(
            label="📄 結果をPDFで保存",
            data=pdf_buffer,
            file_name=f"result_{uuid}.pdf",
            mime="application/pdf"
        )


    else:
        st.warning(
            """
            ⚠️ 入力された情報と登録情報が一致しませんでした。  
            以下をご確認ください：
            - 結果表示用の二次元コードをもう一度読み直してみてください  
            - 誕生日を正しく入力したか（例: 1990-01-01）  
            
            それでも解決しない場合は、下記へご連絡ください：  
            📧 support@example.com
            """
        )

