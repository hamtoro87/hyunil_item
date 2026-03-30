import streamlit as st
import gspread
import json
import pandas as pd
from datetime import datetime

# --- 1. 기본 설정 및 구글 시트 연결 ---
st.set_page_config(page_title="관리자 페이지", layout="wide") 

@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(key_dict)
    return gc

gc = init_connection()

SPREADSHEET_NAME = '창고물품출납대장' # 🚨 꼭 네 파일 이름으로 수정해!
sh = gc.open(SPREADSHEET_NAME)
sheet1 = sh.worksheet("시트1") # 대장 기록용
sheet2 = sh.worksheet("시트2") # 품목 및 재고 연동용

# --- 2. 로그인 세션 관리 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    # 💡 [수정 1] 타이틀을 중앙 정렬하고 줄바꿈해서 보기 좋게 꾸밈!
    st.markdown("""
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: #2e6c80;'>🛡️ 현일고 창고 출납대장</h1>
        <h3 style='color: #777777;'>🔒 관리자 전용 페이지</h3>
    </div>
    """, unsafe_allow_html=True)
    
    with st.container():
        # 로그인 창을 가운데로 예쁘게 모으기 위해 빈 칸(column) 활용
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                pwd = st.text_input("관리자 비밀번호를 입력하세요", type="password")
                # 버튼을 로그인 창 너비에 꽉 차게!
                submit_btn = st.form_submit_button("로그인", use_container_width=True)
                
                if submit_btn:
                    if pwd == "0000":  # 🚨 여기에 원하는 관리자 비밀번호를 설정해!
                        st.session_state['logged_in'] = True
                        st.rerun() 
                    else:
                        st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop() # 로그인이 안 되면 여기서 코드 실행을 멈춤!

# ==========================================
# 🔓 로그인 성공 시 화면
# ==========================================

st.sidebar.title("⚙️ 관리자 메뉴")
menu = st.sidebar.radio("원하는 작업을 선택하세요", ["대장 확인", "재고관리", "사용자관리"])

st.sidebar.markdown("---")
if st.sidebar.button("로그아웃"):
    st.session_state['logged_in'] = False
    st.rerun()

# 📌 [메뉴 1] 대장 확인
if menu == "대장 확인":
    st.subheader("📋 입출고 대장 확인")
    
    try:
        data1 = sheet1.get_all_records()
        if data1:
            df = pd.DataFrame(data1)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("아직 대장에 기록된 내역이 없습니다.")
    except Exception as e:
        st.error("데이터를 불러오는 중 오류가 발생했어. 시트 첫 줄에 제목(헤더)이 잘 적혀있는지 확인해 줘!")

# 📌 [메뉴 2] 재고관리
elif menu == "재고관리":
    st.subheader("📦 창고 재고 및 품목 관리")
    
    data2 = sheet2.get_all_values()
    
    inventory_data = []
    items_dict = {}
    
    for i, row in enumerate(data2[1:], start=2):
        if len(row) > 0 and row[0].strip():
            name = row[0].strip()
            stock = row[1] if len(row) > 1 else "0"
            unit = row[2] if len(row) > 2 else ""
            
            # 표에 보여줄 데이터 모으기
            inventory_data.append({"품명": name, "재고": stock, "단위": unit})
            # 수정할 때 쓸 데이터(시트의 몇 번째 줄인지 등) 모으기
            items_dict[name] = {'row': i, 'stock': stock, 'unit': unit}
    
    # 💡 [수정 2] 현재 재고 상태를 한눈에 볼 수 있게 표로 먼저 쫙 띄워줌!
    if inventory_data:
        df_inv = pd.DataFrame(inventory_data)
        st.markdown("**[현재 창고 재고 현황]**")
        st.dataframe(df_inv, use_container_width=True, hide_index=True)
    else:
        st.warning("등록된 품목이 없습니다.")

    st.markdown("---")
    st.markdown("#### ✏️ 재고 정보 수정")
    
    target_item = st.selectbox("수정할 품명을 선택하세요", ["선택하세요"] + list(items_dict.keys()))
    
    if target_item != "선택하세요":
        row_idx = items_dict[target_item]['row']
        current_stock = items_dict[target_item]['stock']
        current_unit = items_dict[target_item]['unit']
        
        edit_mode = st.checkbox(f"'{target_item}' 데이터 수정하기")
        
        if edit_mode:
            with st.container(border=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_stock = st.number_input("수정할 재고량", value=int(current_stock) if str(current_stock).isdigit() else 0)
                with col2:
                    new_unit = st.text_input("수정할 단위", value=current_unit)
                
                confirm = st.checkbox("진짜로 이 내용으로 수정하시겠습니까? (체크 시 버튼 활성화)")
                
                if st.button("수정 완료 적용하기", disabled=not confirm, type="primary"):
                    try:
                        sheet2.update_cell(row_idx, 2, new_stock)
                        sheet2.update_cell(row_idx, 3, new_unit)
                        st.success("✅ 성공적으로 수정되었습니다! 바뀐 표를 보려면 메뉴를 다시 한 번 클릭(새로고침) 해줘.")
                    except Exception as e:
                        st.error(f"❌ 오류 발생: {e}")

# 📌 [메뉴 3] 사용자관리
elif menu == "사용자관리":
    st.subheader("👥 사용자(담당자) 관리")
    
    col_d = sheet2.col_values(4)
    names_list = [name.strip() for name in col_d[1:] if name.strip()] 
    
    st.markdown("**[현재 등록된 사용자]**")
    for i, name in enumerate(names_list, 1):
        st.write(f"{i}. {name}")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("**➕ 사용자 추가**")
        new_name = st.text_input("새 사용자 이름")
        if st.button("추가하기"):
            if new_name:
                if new_name in names_list:
                    st.warning("이미 등록된 이름입니다.")
                else:
                    next_row = len(col_d) + 1
                    sheet2.update_cell(next_row, 4, new_name)
                    st.success(f"'{new_name}' 추가 완료! (메뉴를 다시 클릭하면 새로고침 돼)")
            else:
                st.error("이름을 입력하세요.")

    with col_right:
        st.markdown("**🗑️ 사용자 삭제**")
        del_name = st.selectbox("삭제할 사용자 선택", ["선택하세요"] + names_list)
        if st.button("삭제하기"):
            if del_name != "선택하세요":
                for i, cell_val in enumerate(col_d):
                    if cell_val.strip() == del_name:
                        sheet2.update_cell(i + 1, 4, "")
                        st.success(f"'{del_name}' 삭제 완료! (메뉴를 다시 클릭하면 새로고침 돼)")
                        break
