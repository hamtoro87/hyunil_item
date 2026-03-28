import streamlit as st
import gspread
from datetime import datetime

# --- 1. 기본 설정 및 구글 시트 연결 ---
# st.cache_resource는 화면이 새로고침될 때마다 매번 구글에 로그인하지 않게 연결 상태를 기억해두는 기능이야.
import json

@st.cache_resource
def init_connection():
    # 스트림릿 비밀 금고(secrets)에서 키 텍스트를 꺼내서 변환하는 마법!
    key_dict = json.loads(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(key_dict)
    return gc

gc = init_connection()

# 네 구글 시트 파일 이름
SPREADSHEET_NAME = '창고물품출납대장' 
sh = gc.open(SPREADSHEET_NAME)

# 시트 이름 (수정했으면 여기서 맞춰줘)
sheet1 = sh.worksheet("시트1") # 대장 기록용
sheet2 = sh.worksheet("시트2") # 품목 및 재고 연동용

# --- 2. 시트2에서 데이터 불러오기 ---
# 데이터를 불러오는 것도 캐싱해두면 좋은데, 재고가 실시간으로 바뀌니까 매번 새로 읽도록 할게.
def load_data():
    data = sheet2.get_all_values()
    items_dict = {}
    names_list = []
    
    # 1행은 제목: A품명, B재고, C단위, D이름 이라고 가정
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

# --- 3. 웹앱 화면 UI 구성 ---
st.title("📦 자재 입출고 관리 앱")
st.markdown("---") # 가로줄 긋기

# 폼(Form) 형태로 묶어주면 '등록' 버튼을 누르기 전까지는 새로고침이 안 돼서 깔끔해.
with st.form("inventory_form", clear_on_submit=True):
    
    # 두 칸으로 나눠서 배치 (왼쪽: 품명, 오른쪽: 이름)
    col1, col2 = st.columns(2)
    
    with col1:
        # 품명 선택 콤보박스
        selected_item = st.selectbox("품명 선택", ["선택하세요"] + item_names)
        
        # 선택한 품명의 단위와 현재 재고 보여주기
        if selected_item != "선택하세요" and selected_item in items_dict:
            unit = items_dict[selected_item]['unit']
            stock = items_dict[selected_item]['stock']
            st.caption(f"단위: {unit} / 현재고: {stock}")

    with col2:
        # 담당자 선택 콤보박스
        selected_name = st.selectbox("담당자 이름", ["선택하세요"] + names_list)

    # 개수 입력 (숫자만, 최소 1)
    qty = st.number_input("개수", min_value=1, step=1)

    # 출납 구분 라디오 버튼
    inout = st.radio("출납구분", ["반출", "반입"], horizontal=True)

    # 비고 텍스트 입력
    note = st.text_input("비고 (선택사항)")

    # 폼 제출 버튼
    submitted = st.form_submit_button("대장에 등록하기", use_container_width=True)

# --- 4. 버튼 눌렀을 때 실행될 로직 ---
if submitted:
    if selected_item == "선택하세요" or selected_name == "선택하세요":
        st.error("⚠️ 품명과 이름을 정확히 선택해 줘!")
    else:
        # 재고 계산
        current_stock = items_dict[selected_item]['stock']
        row_idx = items_dict[selected_item]['row']
        
        if inout == "반출":
            new_stock = current_stock - qty
        else:
            new_stock = current_stock + qty

        try:
            # 1. 시트1 (대장)에 기록 추가
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            col_a = sheet1.col_values(1)
            seq_num = len(col_a) if len(col_a) > 0 else 1
            
            row_data = [seq_num, now_str, selected_item, qty, inout, selected_name, note]
            sheet1.append_row(row_data)

            # 2. 시트2 (물품목록) 재고 업데이트
            sheet2.update_cell(row_idx, 2, new_stock)

            # 3. 성공 메시지 띄우기
            st.success(f"✅ {selected_item} {qty}개가 성공적으로 {inout} 처리됐어! (남은 재고: {new_stock})")
            
        except Exception as e:
            st.error(f"❌ 저장 중 오류가 발생했어: {e}")
