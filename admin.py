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

SPREADSHEET_NAME = '창고물품출납대장' # 🚨 꼭 네 파일 이름으로 수정!
sh = gc.open(SPREADSHEET_NAME)
sheet1 = sh.worksheet("시트1") 
sheet2 = sh.worksheet("시트2") 

# --- 2. 로그인 및 세션 상태 초기화 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# 💡 [신규] 방금 등록한 물품 목록을 저장할 저장소 만들기
if 'added_items_history' not in st.session_state:
    st.session_state['added_items_history'] = []

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
                if pwd == "0000": # 🚨 비밀번호
                    st.session_state['logged_in'] = True
                    st.rerun() 
                else:
                    st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop()

# ==========================================
# 🔓 관리자 메뉴 시작
# ==========================================

st.sidebar.title("⚙️ 관리자 메뉴")
menu = st.sidebar.radio("원하는 작업을 선택하세요", ["대장 확인", "재고관리", "물품입고", "사용자관리"])

st.sidebar.markdown("---")
if st.sidebar.button("로그아웃"):
    st.session_state['logged_in'] = False
    st.session_state['added_items_history'] = [] # 로그아웃 시 기록 삭제
    st.rerun()

# 📌 [메뉴 1] 대장 확인
if menu == "대장 확인":
    st.subheader("📋 입출고 대장 확인")
    data1 = sheet1.get_all_records()
    if data1:
        st.dataframe(pd.DataFrame(data1), use_container_width=True, hide_index=True)
    else:
        st.info("기록된 내역이 없습니다.")

# 📌 [메뉴 2] 재고관리
elif menu == "재고관리":
    st.subheader("📦 창고 재고 및 품목 관리")
    data2 = sheet2.get_all_values()
    inventory_data = [{"품명": r[0].strip(), "재고": r[1], "단위": r[2]} for r in data2[1:] if r[0].strip()]
    
    if inventory_data:
        st.dataframe(pd.DataFrame(inventory_data), use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.markdown("#### ✏️ 재고 정보 수정")
    item_list = [d["품명"] for d in inventory_data]
    target_item = st.selectbox("수정할 품명을 선택하세요", ["선택하세요"] + item_list)
    
    if target_item != "선택하세요":
        # 해당 품목 정보 찾기
        item_row = next(i+2 for i, r in enumerate(data2[1:]) if r[0].strip() == target_item)
        item_info = next(d for d in inventory_data if d["품명"] == target_item)
        
        edit_mode = st.checkbox(f"'{target_item}' 수정 모드 활성화")
        if edit_mode:
            with st.container(border=True):
                col1, col2 = st.columns(2)
                new_stock = col1.number_input("수정 재고량", value=int(item_info['재고']) if str(item_info['재고']).isdigit() else 0)
                new_unit = col2.text_input("수정 단위", value=item_info['단위'])
                confirm = st.checkbox("데이터를 수정하려면 체크해 주세요.")
                
                if st.button("수정 완료 적용", disabled=not confirm, type="primary"):
                    sheet2.update_cell(item_row, 2, new_stock)
                    sheet2.update_cell(item_row, 3, new_unit)
                    st.success("✅ 수정 완료!")
                    time.sleep(1)
                    st.rerun()

# 📌 [메뉴 3] 물품입고 (💡 기록 보관 기능 추가)
elif menu == "물품입고":
    st.subheader("🆕 신규 물품 등록")
    
    with st.form("new_item_form", clear_on_submit=True):
        new_name = st.text_input("신규 품명")
        col1, col2 = st.columns(2)
        new_stock = col1.number_input("초기 재고량", min_value=0, step=1)
        new_unit = col2.text_input("단위")
        submit_btn = st.form_submit_button("신규 물품 등록", use_container_width=True)
        
        if submit_btn:
            if new_name and new_unit:
                # 1. 구글 시트에 저장
                sheet2.append_row([new_name, new_stock, new_unit])
                
                # 2. 💡 [핵심] 세션 히스토리에 방금 입력한 거 추가
                now = datetime.now().strftime("%H:%M:%S")
                history_entry = {"등록 시간": now, "품명": new_name, "초기 재고": new_stock, "단위": new_unit}
                # 최신 것이 위로 오게 리스트 맨 앞에 삽입
                st.session_state['added_items_history'].insert(0, history_entry)
                
                st.success(f"✅ '{new_name}' 등록 완료!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("품명과 단위를 입력하세요.")

    # 💡 등록한 목록 순차적으로 보여주는 영역
    if st.session_state['added_items_history']:
        st.markdown("---")
        st.markdown("#### 🕒 방금 등록한 목록 (최신순)")
        history_df = pd.DataFrame(st.session_state['added_items_history'])
        st.table(history_df) # 깔끔하게 표 형태로 띄워줌
        
        if st.button("목록 비우기"):
            st.session_state['added_items_history'] = []
            st.rerun()

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
                time.sleep(1); st.rerun()

    with col_right:
        st.markdown("**🗑️ 삭제**")
        del_user = st.selectbox("삭제할 이름", ["선택하세요"] + names_list)
        if st.button("삭제"):
            if del_user != "선택하세요":
                for i, val in enumerate(col_d):
                    if val.strip() == del_user:
                        sheet2.update_cell(i + 1, 4, "")
                        st.success("삭제 완료!"); time.sleep(1); st.rerun(); break
