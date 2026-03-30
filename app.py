import streamlit as st
import gspread
import json
from datetime import datetime

# 📱 1. 모바일 화면에 맞게 꽉 차는 레이아웃 설정 (반드시 코드 제일 위에 있어야 함!)
st.set_page_config(page_title="현일고 창고 출납대장", layout="centered")

# --- 2. 구글 시트 연결 (비밀 금고 사용) ---
@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(key_dict)
    return gc

gc = init_connection()

# 네 스프레드시트 이름 (여기 꼭 네 파일 이름으로 수정해!)
SPREADSHEET_NAME = '창고물품출납대장' 
sh = gc.open(SPREADSHEET_NAME)
sheet1 = sh.worksheet("시트1") # 대장 기록용
sheet2 = sh.worksheet("시트2") # 품목 및 재고 연동용

# --- 3. 시트2에서 데이터 불러오기 ---
def load_data():
    data = sheet2.get_all_values()
    items_dict = {}
    names_list = []
    
    for i, row in enumerate(data[1:], start=2):
        if len(row) > 0 and row[0].strip():
            name = row[0].strip()
            stock = int(row[1]) if len(row) > 1 and row[1].isdigit() else 0
            unit = row[2].strip() if len(row) > 2 else ""
            items_dict[name] = {'row': i, 'stock': stock, 'unit': unit}
            
        if len(row) > 3 and row[3].strip():
            person_name = row[3].strip()
            if person_name not in names_list:
                names_list.append(person_name)
                
    return items_dict, names_list

items_dict, names_list = load_data()
item_names = list(items_dict.keys())

# --- 4. 웹앱 화면 UI 구성 ---
# 제목 변경 적용
st.title("📦 현일고 창고 출납대장")

# 💡 [핵심 수정] 폼(Form) 바깥으로 품명 선택을 빼서 누르자마자 즉각 반응하게 만듦!
selected_item = st.selectbox("품명 선택", ["선택하세요"] + item_names)

# 선택하면 바로 아래에 재고량과 단위가 눈에 띄게 표시됨
if selected_item != "선택하세요" and selected_item in items_dict:
    unit = items_dict[selected_item]['unit']
    stock = items_dict[selected_item]['stock']
    st.info(f"현재 남은 재고: **{stock}** {unit}")
else:
    st.write("") # 선택 안 했을 때는 빈 공간 유지

st.markdown("---")

# 나머지 입력칸들만 폼으로 묶기
with st.form("inventory_form", clear_on_submit=True):
    
    col1, col2 = st.columns(2)
    with col1:
        inout = st.radio("출납구분", ["반출", "반입"], horizontal=True)
    with col2:
        qty = st.number_input("개수", min_value=1, step=1)
        
    selected_name = st.selectbox("사용자 이름", ["선택하세요"] + names_list)
    note = st.text_input("비고 (선택사항)")

    # 모바일에서 버튼이 화면 너비에 꽉 차도록 큼직하게 만들기
    submitted = st.form_submit_button("대장에 등록하기", use_container_width=True)

# --- 5. 버튼 눌렀을 때 실행될 로직 ---
if submitted:
    if selected_item == "선택하세요":
        st.error("⚠️ 위에서 품명을 먼저 선택하세요.")
    elif selected_name == "선택하세요":
        st.error("⚠️ 담당자 이름을 선택하세요.")
    else:
        current_stock = items_dict[selected_item]['stock']
        row_idx = items_dict[selected_item]['row']
        
        if inout == "반출":
            new_stock = current_stock - qty
        else:
            new_stock = current_stock + qty

        try:
            # 시간은 폰에서 등록 누르는 순간 자동으로 딱 찍힘
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            col_a = sheet1.col_values(1)
            seq_num = len(col_a) if len(col_a) > 0 else 1
            
            row_data = [seq_num, now_str, selected_item, qty, inout, selected_name, note]
            sheet1.append_row(row_data)
            sheet2.update_cell(row_idx, 2, new_stock)

            st.success(f"✅ {selected_item} {qty}개가 성공적으로 {inout} 처리되었습니다. (남은 재고: {new_stock})")
            
        except Exception as e:
            st.error(f"❌ 저장 중 오류가 발생했어: {e}")
