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

# --- Supabase 設定 ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]  # RLS用
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
st.write(supabase_URL)

# フォント登録
FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "ipaexg.ttf")
if not os.path.exists(FONT_PATH):
    raise FileNotFoundError(f"{FONT_PATH} が見つかりません")
pdfmetrics.registerFont(TTFont('IPAexGothic', FONT_PATH))

# --- タイトル ---
st.title("健康チェック結果ページ 🩺")

# --- URLのパラメータからUUID取得 ---
params = st.query_params
uuid = params.get("uuid", [""])

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

# --- 入力フォーム ---
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

        # 実年齢計算
        birth_date = datetime.datetime.fromisoformat(data['bday']).date()
        today = datetime.date.today()
        real_age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        st.warning("⚠️ この結果はAIによる健康リスク推定です。診断ではありません。")
        st.caption("気になる点がある場合は、必ず医療機関にご相談ください。")

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

        # 画像表示（右目・左目）
        st.subheader("👁️ 撮影画像")
        right_img = data.get("image_url_right")
        left_img = data.get("image_url_left")

        num_cols = 2 if st.session_state.get("screen_width", 0) > 600 else 1
        cols = st.columns(num_cols)

        if right_img:
            cols[0].image(right_img, caption="右目", use_container_width=True)
        else:
            cols[0].info("右目の画像は未撮影です。")
        left_col = cols[1] if num_cols == 2 else st
        if left_img:
            left_col.image(left_img, caption="左目", use_container_width=True)
        else:
            left_col.info("左目の画像は未撮影です。")
        
        # -------------------------
        # AIによる目の健康評価
        # -------------------------
        st.subheader("🔎 AIによる目の健康評価")
        if not data.get("fundus_age") and not data.get("glaucoma_risk") and not data.get("atherosclerosis_risk"):
            st.info(
                """
                ⚡ 現在、AIによる解析中です。
                """
            )
        else:

            if "fundus_age" in data:
                fundus_age = data["fundus_age"]
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
            def render_risk(label: str, risk_level: str):
                st.markdown(f"### {label}")
                if risk_level.lower() == "low":
                    st.success("リスク：低 🟢 安心できる状態です。")
                elif risk_level.lower() == "medium":
                    st.warning("リスク：中 🟡 健康に気をつけて生活習慣を見直しましょう。")
                elif risk_level.lower() == "high":
                    st.error("リスク：高 🔴 気になる場合は専門家に相談すると安心です。")
                else:
                    st.info(f"リスク：{risk_level}")

            if "glaucoma_risk" in data:
                render_risk("緑内障リスク", data["glaucoma_risk"])
            if "atherosclerosis_risk" in data:
                render_risk("動脈硬化リスク", data["atherosclerosis_risk"])

        # -------------------------
        # PDF生成
        # -------------------------
        def generate_pdf(data, uuid, real_age):
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            width, height = A4
            y = height - 40

            # タイトル
            c.setFont("Helvetica-Bold", 18)
            c.drawCentredString(width/2, y, "AIによる目の健康評価 結果")
            y -= 40

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

            # 眼底写真サムネイル
            c.setFont("IPAexGothic", 14)
            c.drawString(20, y, "撮影画像")
            y -= 20
            thumb_height = 60*mm
            thumb_width = 60*mm

            if data.get("image_url_right"):
                right_img = Image.open(data["image_url_right"])
                c.setFont("IPAexGothic", 14)
                c.drawImage(ImageReader(right_img), 50, y - thumb_height, width=thumb_width, height=thumb_height)
                c.setFont("IPAexGothic", 14)
                c.drawString(50, y - thumb_height - 12, "右目")
            if data.get("image_url_left"):
                left_img = Image.open(data["image_url_left"])
                x_offset = 50 + thumb_width + 20 if data.get("image_url_right") else 50
                c.drawImage(ImageReader(left_img), x_offset, y - thumb_height, width=thumb_width, height=thumb_height)
                c.setFont("IPAexGothic", 14)
                c.drawString(x_offset, y - thumb_height - 12, "左目")
            y -= thumb_height + 30

            # AI評価
            c.setFont("IPAexGothic", 14)
            c.drawString(20, y, "🔎 AIによる目の健康評価")
            y -= 20
            c.setFont("IPAexGothic", 12)

            if "fundus_age" in data:
                fundus_age = data["fundus_age"]
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
            def render_risk_pdf(label, risk_level, y_pos):
                c.setFont("IPAexGothic", 14)
                c.drawString(30, y_pos, f"{label}: {risk_level}")
                y_pos -= 16
                if risk_level.lower() == "low":
                    c.setFont("IPAexGothic", 14)
                    c.drawString(35, y_pos, "低：安心できる状態です")
                elif risk_level.lower() == "medium":
                    c.setFont("IPAexGothic", 14)
                    c.drawString(35, y_pos, "中：健康に気をつけて生活習慣を見直しましょう")
                elif risk_level.lower() == "high":
                    c.setFont("IPAexGothic", 14)
                    c.drawString(35, y_pos, "高：気になる場合は専門家に相談すると安心です")
                return y_pos - 16

            if "glaucoma_risk" in data:
                y = render_risk_pdf("緑内障リスク", data["glaucoma_risk"], y)
            if "atherosclerosis_risk" in data:
                y = render_risk_pdf("動脈硬化リスク", data["atherosclerosis_risk"], y)

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

