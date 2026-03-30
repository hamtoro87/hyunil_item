import streamlit as st
import gspread
import json
import pandas as pd
from datetime import datetime
import time

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
sheet1 = sh.worksheet("시트1") 
sheet2 = sh.worksheet("시트2") 

# --- 2. 로그인 세션 관리 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("""
    <div style='text-align: center; margin-bottom: 30px;'>
        <h1 style='color: #2e6c80;'>🛡️ 현일고 창고 출납대장</h1>
        <h3 style='color: #777777;'>🔒 관리자 전용 페이지</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            pwd = st.text_input("관리자 비밀번호를 입력하세요", type="password")
            submit_btn = st.form_submit_button("로그인", use_container_width=True)
            if submit_btn:
                if pwd == "0000": # 🚨 비밀번호 설정
                    st.session_state['logged_in'] = True
                    st.rerun() 
                else:
                    st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# ==========================================
# 🔓 로그인 성공 시 화면
# ==========================================

st.sidebar.title("⚙️ 관리자 메뉴")
# 💡 [메뉴 추가] '물품입고' 메뉴가 새로 생겼어!
menu = st.sidebar.radio("원하는 작업을 선택하세요", ["대장 확인", "재고관리", "물품입고", "사용자관리"])

st.sidebar.markdown("---")
if st.sidebar.button("로그아웃"):
    st.session_state['logged_in'] = False
    st.rerun()

# 📌 [메뉴 1] 대장 확인
if menu == "대장 확인":
    st.subheader("📋 입출고 대장 확인")
    data1 = sheet1.get_all_records()
    if data1:
        st.dataframe(pd.DataFrame(data1), use_container_width=True, hide_index=True)
    else:
        st.info("기록된 내역이 없습니다.")

# 📌 [메뉴 2] 재고관리 (수정 시 실시간 반영 로직 추가)
elif menu == "재고관리":
    st.subheader("📦 창고 재고 및 품목 관리")
    
    data2 = sheet2.get_all_values()
    inventory_data = []
    items_dict = {}
    
    for i, row in enumerate(data2[1:], start=2):
        if len(row) > 0 and row[0].strip():
            name, stock, unit = row[0].strip(), row[1], row[2]
            inventory_data.append({"품명": name, "재고": stock, "단위": unit})
            items_dict[name] = {'row': i, 'stock': stock, 'unit': unit}
    
    if inventory_data:
        st.dataframe(pd.DataFrame(inventory_data), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("#### ✏️ 재고 정보 수정")
    target_item = st.selectbox("수정할 품명을 선택하세요", ["선택하세요"] + list(items_dict.keys()))
    
    if target_item != "선택하세요":
        item_info = items_dict[target_item]
        edit_mode = st.checkbox(f"'{target_item}' 수정 모드 활성화")
        
        if edit_mode:
            with st.container(border=True):
                col1, col2 = st.columns(2)
                new_stock = col1.number_input("수정 재고량", value=int(item_info['stock']) if str(item_info['stock']).isdigit() else 0)
                new_unit = col2.text_input("수정 단위", value=item_info['unit'])
                confirm = st.checkbox("데이터를 수정하는 것에 동의해!")
                
                if st.button("수정 완료 적용", disabled=not confirm, type="primary"):
                    sheet2.update_cell(item_info['row'], 2, new_stock)
                    sheet2.update_cell(item_info['row'], 3, new_unit)
                    st.success("✅ 수정 완료! 화면을 다시 불러옵니다.")
                    time.sleep(1) # 메시지 볼 시간 1초 주기
                    st.rerun() # 💡 여기서 앱을 다시 실행해서 표를 즉시 업데이트!

# 📌 [메뉴 3] 물품입고 (신규 품목 등록 기능)
elif menu == "물품입고":
    st.subheader("🆕 신규 물품 등록")
    st.info("창고에 새로운 물건을 처음 들여올 때 여기서 등록하세요.")
    
    with st.form("new_item_form", clear_on_submit=True):
        new_name = st.text_input("신규 품명 (예: A4용지)")
        col1, col2 = st.columns(2)
        new_stock = col1.number_input("초기 재고량", min_value=0, step=1)
        new_unit = col2.text_input("단위 (예: 박스, 개)")
        
        submit_btn = st.form_submit_button("신규 물품 등록하기", use_container_width=True)
        
        if submit_btn:
            if new_name and new_unit:
                # 시트2의 A, B, C열에 데이터 추가 (D열은 사용자 이름이니까 건드리지 않음)
                # 시트의 맨 아래에 행을 추가하는 방식이야.
                sheet2.append_row([new_name, new_stock, new_unit])
                st.success(f"✅ '{new_name}' 물품이 등록되었습니다.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("품명과 단위를 모두 입력하세요.")

# 📌 [메뉴 4] 사용자관리
elif menu == "사용자관리":
    st.subheader("👥 사용자(담당자) 관리")
    col_d = sheet2.col_values(4)
    names_list = [name.strip() for name in col_d[1:] if name.strip()] 
    
    for i, name in enumerate(names_list, 1):
        st.write(f"{i}. {name}")
    
    st.markdown("---")
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("**➕ 추가**")
        new_user = st.text_input("새 이름")
        if st.button("추가"):
            if new_user and new_user not in names_list:
                sheet2.update_cell(len(col_d) + 1, 4, new_user)
                st.success("추가 완료!")
                time.sleep(1)
                st.rerun()

    with col_right:
        st.markdown("**🗑️ 삭제**")
        del_user = st.selectbox("삭제할 이름", ["선택하세요"] + names_list)
        if st.button("삭제"):
            if del_user != "선택하세요":
                for i, val in enumerate(col_d):
                    if val.strip() == del_user:
                        sheet2.update_cell(i + 1, 4, "")
                        st.success("삭제 완료!")
                        time.sleep(1)
                        st.rerun()
                        break
