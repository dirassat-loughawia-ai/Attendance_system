import io
import urllib.request
import os
from datetime import datetime
import pandas as pd
import streamlit as st

# مكتبات معالجة وتشكيل النص العربي للـ PDF
import arabic_reshaper
from bidi.algorithm import get_display

# مكتبات ReportLab لتوليد ملفات الـ PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ----------------------------------------------------
# 1. تحميل الخط العربي المعتمد لتفادي المربعات
# ----------------------------------------------------
FONT_PATH = "Amiri-Regular.ttf"
if not os.path.exists(FONT_PATH):
    try:
        url = "https://github.com/google/fonts/raw/main/ofl/amiri/Amiri-Regular.ttf"
        urllib.request.urlretrieve(url, FONT_PATH)
    except Exception:
        pass

# ----------------------------------------------------
# 2. إعدادات الصفحة والتصميم المتجاوب
# ----------------------------------------------------
st.set_page_config(
    page_title="برنامج إدارة غيابات الطلبة",
    page_icon="🎓",
    layout="wide"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: rtl;
        text-align: right;
    }
    
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 16px 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .main-header h2 {
        margin: 0;
        font-size: 22px;
        font-weight: 700;
        color: #ffffff;
    }

    .notice-box {
        background-color: #eef2f7;
        border-right: 4px solid #1e3c72;
        padding: 10px 15px;
        border-radius: 6px;
        font-weight: 600;
        color: #1e3c72;
        margin-bottom: 12px;
    }

    /* جعل اتجاه الجدول من اليمين إلى اليسار */
    div[data-testid="stDataFrame"] {
        direction: rtl !important;
        text-align: right !important;
    }

    .stDownloadButton > button, .stButton > button {
        width: 100%;
        background-color: #1e3c72;
        color: white;
        border-radius: 8px;
        font-weight: bold;
        padding: 12px;
        border: none;
        font-size: 16px;
        transition: background-color 0.3s;
    }

    .stDownloadButton > button:hover, .stButton > button:hover {
        background-color: #2a5298;
    }
    </style>
""", unsafe_allow_html=True)


# ----------------------------------------------------
# 3. دالة المطابقة الذكية لأسماء الأساتذة
# ----------------------------------------------------
def smart_name_match(name1, name2):
    """تطابق الأسماء بغض النظر عن ترتيب الكلمات (مثال: مليك جوادي == جوادي مليك)"""
    if pd.isna(name1) or pd.isna(name2):
        return False
    words1 = set(str(name1).strip().split())
    words2 = set(str(name2).strip().split())
    return words1 == words2 and len(words1) > 0


# ----------------------------------------------------
# 4. دالة معالجة النصوص العربية
# ----------------------------------------------------
def fix_arabic(text):
    if not text or pd.isna(text):
        return ""
    reshaped_text = arabic_reshaper.reshape(str(text))
    return get_display(reshaped_text)


# ----------------------------------------------------
# 5. دالة إنشاء ملف الـ PDF
# ----------------------------------------------------
def create_pdf(teacher_name, session_info):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # تسجيل الخط العربي
    if os.path.exists(FONT_PATH):
        pdfmetrics.registerFont(TTFont('ArabicFont', FONT_PATH))
        font_name = 'ArabicFont'
    else:
        font_name = 'Helvetica'

    # --- الترويسة العليا ---
    c.setFont(font_name, 11)
    c.drawCentredString(width / 2, height - 40, fix_arabic("الجمهورية الجزائرية الديمقراطية الشعبية"))
    c.drawCentredString(width / 2, height - 58, fix_arabic("وزارة التعليم العالي والبحث العلمي"))
    c.drawCentredString(width / 2, height - 76, fix_arabic("جامعة الوادي"))

    c.drawRightString(width - 45, height - 96, fix_arabic("كلية الآداب واللغات"))
    c.drawString(45, height - 96, fix_arabic("السنة الجامعية: 2026-2027"))
    c.drawRightString(width - 45, height - 111, fix_arabic("قسم اللغة والأدب العربي"))

    # --- عنوان التقرير ---
    title_y = height - 160
    c.setFont(font_name, 18)
    c.drawCentredString(width / 2, title_y, fix_arabic("تقرير غياب جماعي للطلبة"))

    # --- نص التقرير والمعلومات ---
    c.setFont(font_name, 11)
    y_pos = title_y - 45
    
    c.drawRightString(width - 45, y_pos, fix_arabic("لقد سجلنا غياباً جماعياً للطلبة وفقاً للمعلومات الآتية:"))
    
    y_pos -= 22
    c.drawRightString(width - 45, y_pos, fix_arabic(f"• أستاذ المادة: {teacher_name}"))

    # استبعاد الأرقام المعرفة وأسماء الأساتذة من التقرير
    ignored_keys = ['اسم الأستاذ', 'الرقم', 'رقم', 'الرقم التسلسلي', 'id', 'ID', 'no', 'No', 'الرقم السري']
    
    for key, val in session_info.items():
        if key not in ignored_keys and not any(k in str(key) for k in ['الرقم', 'رقم']):
            y_pos -= 22
            c.drawRightString(width - 45, y_pos, fix_arabic(f"• {key}: {val}"))

    # ترك مسافة فارغة
    y_pos -= 80

    # التاريخ والتوقيع في أقصى اليسار
    today_date = datetime.now().strftime("%Y-%m-%d")
    c.drawString(45, y_pos, fix_arabic(f"حرر بتاريخ: {today_date}"))

    y_pos -= 25
    c.drawString(45, y_pos, fix_arabic("توقيع الأستاذ(ة):"))

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# ----------------------------------------------------
# 6. شاشة كلمة المرور الرئيسية (ADMIN)
# ----------------------------------------------------
if 'admin_authenticated' not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.markdown("""
        <div class="main-header">
            <h2>🔐 التأكد من هوية المستخدم</h2>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        master_password = st.text_input("أدخل كلمة السر العامة للدخول:", type="password", key="admin_pass")
        if st.button("دخول البرنامج"):
            if master_password == "ADMIN":
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("كلمة المرور العامة غير صحيحة!")
    st.stop()


# ----------------------------------------------------
# 7. الواجهة الرئيسية للبرنامج
# ----------------------------------------------------
st.markdown("""
    <div class="main-header">
        <h2>برنامج إدارة غيابات الطلبة</h2>
    </div>
""", unsafe_allow_html=True)

# قراءة البيانات
try:
    df_teachers = pd.read_excel('teachers.xlsx')
    df_sessions = pd.read_excel('sessions.xlsx')

    df_teachers.columns = df_teachers.columns.astype(str).str.strip()
    df_sessions.columns = df_sessions.columns.astype(str).str.strip()
except Exception:
    st.error("⚠ يتعذر قراءة الملفات. يرجى التأكد من توفر ملفات 'teachers.xlsx' و 'sessions.xlsx'.")
    st.stop()

teacher_col = df_teachers.columns[0]
pass_col = df_teachers.columns[1]

session_teacher_col = [c for c in df_sessions.columns if 'أستاذ' in c or 'الاستاذ' in c or 'اسم' in c]
session_teacher_key = session_teacher_col[0] if session_teacher_col else df_sessions.columns[0]

# تسجيل دخول الأستاذ
c1, c2 = st.columns(2)
teachers_list = df_teachers[teacher_col].dropna().astype(str).str.strip().unique().tolist()

with c1:
    selected_teacher = st.selectbox("اسم الأستاذ:", ["-- اختر الاسم --"] + teachers_list)
with c2:
    password_input = st.text_input("الرقم السري للأستاذ:", type="password")

if selected_teacher != "-- اختر الاسم --" and password_input:
    teacher_row = df_teachers[df_teachers[teacher_col].astype(str).str.strip() == selected_teacher]
    real_password = str(teacher_row.iloc[0][pass_col]).strip()

    if password_input.strip() == real_password:
        st.success(f"مرحباً بك أستاذ(ة) {selected_teacher}")
        
        # المطابقة الذكية للأسماء بين ملف الحصص وملف الرقم السري
        matching_rows = []
        for idx, row in df_sessions.iterrows():
            if smart_name_match(selected_teacher, row[session_teacher_key]):
                matching_rows.append(row)

        teacher_sessions = pd.DataFrame(matching_rows)

        # التعامل الآمن مع عمود "الرقم" لتجنب خطأ التكرار
        if not teacher_sessions.empty:
            teacher_sessions = teacher_sessions.reset_index(drop=True)
            
            if 'الرقم' in teacher_sessions.columns:
                teacher_sessions['الرقم'] = range(1, len(teacher_sessions) + 1)
            else:
                teacher_sessions.insert(0, 'الرقم', range(1, len(teacher_sessions) + 1))
            
            # إخفاء عمود اسم الأستاذ من جدول العرض
            cols = list(teacher_sessions.columns)
            if session_teacher_key in cols:
                cols.remove(session_teacher_key)
            teacher_sessions = teacher_sessions[cols]

        st.markdown("---")

        # خيار إضافة حصة جديدة أو اختيار حصة مسجلة
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            show_custom_session = st.toggle("➕ إضافة حصة أخرى غير مدرجة", value=False)

        if show_custom_session:
            st.markdown("##### 📝 إدخال تفاصيل الحصة الجديدة:")
            
            c_day, c_time = st.columns(2)
            with c_day:
                custom_day = st.selectbox("اليوم:", ["الأحد", "الإثنين", "الثلاثاء", "الأربعاء", "الخميس", "السبت"])
            with c_time:
                custom_time = st.selectbox("التوقيت:", ["08:00 - 09:30", "09:30 - 11:00", "11:00 - 12:30", "12:30 - 14:00", "14:00 - 15:30", "15:30 - 17:00"])

            c_sub, c_room = st.columns(2)
            with c_sub:
                custom_subject = st.text_input("المادة:")
            with c_room:
                custom_room = st.text_input("القاعة / المدرج:")

            c_stage, c_spec = st.columns(2)
            with c_stage:
                custom_stage = st.text_input("الطور (ليسانس / ماستر):")
            with c_spec:
                custom_spec = st.text_input("التخصص:")

            c_year, c_group = st.columns(2)
            with c_year:
                custom_year = st.text_input("السنة:")
            with c_group:
                custom_group = st.text_input("الفوج:")

            custom_data = {
                "اليوم": custom_day,
                "التوقيت": custom_time,
                "المادة": custom_subject,
                "القاعة": custom_room,
                "الطور": custom_stage,
                "التخصص": custom_spec,
                "السنة": custom_year,
                "الفوج": custom_group
            }

            st.markdown("<br>", unsafe_allow_html=True)
            pdf_data = create_pdf(selected_teacher, custom_data)
            st.download_button(
                label="🖨️️ طباعة تقرير الحصة الجديدة (PDF)",
                data=pdf_data,
                file_name=f"تقرير_غياب_{selected_teacher}.pdf",
                mime="application/pdf"
            )

        else:
            if teacher_sessions.empty:
                st.warning("لا توجد حصص مسجلة باسمك حالياً في القاعدة.")
            else:
                st.markdown("""
                    <div class="notice-box">
                        👇 حدد الحصة المراد طباعتها بالنقر عليها من الجدول:
                    </div>
                """, unsafe_allow_html=True)

                # عرض الجدول بدون إمكانية التعديل
                event = st.dataframe(
                    teacher_sessions,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="single-row"
                )

                selected_rows = event.selection.rows if event and hasattr(event, 'selection') else []

                if len(selected_rows) > 0:
                    selected_index = selected_rows[0]
                    selected_row = teacher_sessions.iloc[selected_index].to_dict()

                    st.markdown("<br>", unsafe_allow_html=True)
                    pdf_data = create_pdf(selected_teacher, selected_row)

                    st.download_button(
                        label="🖨 طباعة تقرير الغياب للحصة المختارة (PDF)",
                        data=pdf_data,
                        file_name=f"تقرير_غياب_{selected_teacher}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.info("💡 انقر على أحد أسطر الجدول لتحديد الحصة وطباعة التقرير.")
    else:
        st.error("الرقم السري الخاص بالأستاذ غير صحيح.")