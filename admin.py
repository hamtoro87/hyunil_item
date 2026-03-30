import streamlit as st
import gspread
import json
import pandas as pd
from datetime import datetime

# --- 1. 기본 설정 및 구글 시트 연결 ---
st.set_page_config(page_title="관리자 페이지", layout="wide") # 관리자용은 표를 넓게 보기 위해 wide 모드

@st.cache_resource
def init_connection():
    key_dict = json.loads(st.secrets["gcp_service_account"])
    gc = gspread.service_account_from_dict(key_dict)
    return gc

gc = init_connection()

SPREADSHEET_NAME = '창고물품출납대장' 
sh = gc.open(SPREADSHEET_NAME)
sheet1 = sh.worksheet("시트1") # 대장 기록용
sheet2 = sh.worksheet("시트2") # 품목 및 재고 연동용

# --- 2. 로그인 세션 관리 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# 로그인이 안 되어 있다면 로그인 화면만 띄움
if not st.session_state['logged_in']:
    st.title("🛡️ 현일고 창고 출납대장 관리자 페이지")
    st.markdown("---")
    
    # 폼으로 묶어서 엔터 쳐도 로그인이 되게 만듦
    with st.form("login_form"):
        pwd = st.text_input("관리자 비밀번호를 입력하세요", type="password")
        submit_btn = st.form_submit_button("로그인")
        
        if submit_btn:
            if pwd == "0000":  # 🚨 여기에 원하는 관리자 비밀번호를 설정해!
                st.session_state['logged_in'] = True
                st.rerun() # 화면 새로고침해서 관리자 메뉴로 진입
            else:
                st.error("❌ 비밀번호가 틀렸습니다.")
    st.stop() # 로그인이 안 되면 여기서 코드 실행을 멈춤! (아래 화면 안 보임)

# ==========================================
# 🔓 여기서부터는 로그인 성공 시 보이는 화면
# ==========================================

# --- 3. 사이드바 메뉴 설정 ---
st.sidebar.title("⚙️ 관리자 메뉴")
menu = st.sidebar.radio("원하는 작업을 선택하세요", ["대장 확인", "재고관리", "사용자관리"])

st.sidebar.markdown("---")
if st.sidebar.button("로그아웃"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- 4. 메뉴별 기능 구현 ---

# 📌 [메뉴 1] 대장 확인
if menu == "대장 확인":
    st.subheader("📋 입출고 대장 확인")
    
    # 시트1의 모든 데이터를 가져와서 깔끔한 표(데이터프레임)로 변환
    data1 = sheet1.get_all_records()
    if data1:
        df = pd.DataFrame(data1)
        # 스트림릿의 데이터프레임 기능으로 깔끔하고 정렬 가능한 표 출력
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("아직 대장에 기록된 내역이 없습니다.")

# 📌 [메뉴 2] 재고관리
elif menu == "재고관리":
    st.subheader("📦 창고 재고 및 품목 관리")
    
    data2 = sheet2.get_all_values()
    # 첫 행(제목) 제외하고 딕셔너리로 묶기
    items_dict = {row[0].strip(): {'row': i, 'stock': row[1], 'unit': row[2]} 
                  for i, row in enumerate(data2[1:], start=2) if len(row) > 0 and row[0].strip()}
    
    target_item = st.selectbox("관리할 품명을 선택하세요", ["선택하세요"] + list(items_dict.keys()))
    
    if target_item != "선택하세요":
        row_idx = items_dict[target_item]['row']
        current_stock = items_dict[target_item]['stock']
        current_unit = items_dict[target_item]['unit']
        
        # 현재 상태 보여주기
        st.info(f"현재 재고: **{current_stock}** | 현재 단위: **{current_unit}**")
        
        # 수정 체크박스 (이걸 체크해야 폼이 열림)
        edit_mode = st.checkbox("이 품목 수정하기")
        
        if edit_mode:
            with st.container(border=True):
                st.write("수정할 내용을 입력하세요:")
                col1, col2 = st.columns(2)
                with col1:
                    new_stock = st.number_input("수정할 재고량", value=int(current_stock) if current_stock.isdigit() else 0)
                with col2:
                    new_unit = st.text_input("수정할 단위", value=current_unit)
                
                # 확인 체크박스 (이걸 체크해야 버튼이 활성화됨)
                confirm = st.checkbox("진짜로 이 내용으로 수정하시겠습니까? (체크 시 버튼 활성화)")
                
                # disabled 속성으로 체크박스 상태와 연동
                if st.button("수정 완료 적용하기", disabled=not confirm, type="primary"):
                    try:
                        sheet2.update_cell(row_idx, 2, new_stock)
                        sheet2.update_cell(row_idx, 3, new_unit)
                        st.success("✅ 성공적으로 수정되었습니다! 변경 사항을 보려면 다른 메뉴를 눌렀다 돌아오세요.")
                    except Exception as e:
                        st.error(f"❌ 오류 발생: {e}")

# 📌 [메뉴 3] 사용자관리
elif menu == "사용자관리":
    st.subheader("👥 사용자(담당자) 관리")
    
    # 4번째 열(D열) 이름 목록 가져오기
    col_d = sheet2.col_values(4)
    names_list = [name.strip() for name in col_d[1:] if name.strip()] # 제목 제외하고 빈칸 제거
    
    # 1. 현재 사용자 목록 보여주기 (임의의 숫자 붙여서)
    st.markdown("**[현재 등록된 사용자]**")
    for i, name in enumerate(names_list, 1):
        st.write(f"{i}. {name}")
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    
    # 2. 사용자 추가
    with col_left:
        st.markdown("**사용자 추가**")
        new_name = st.text_input("새 사용자 이름")
        if st.button("추가하기"):
            if new_name:
                if new_name in names_list:
                    st.warning("이미 등록된 이름입니다.")
                else:
                    # 빈칸 찾아서 넣기 (간단하게 D열 맨 끝 행에 추가)
                    next_row = len(col_d) + 1
                    sheet2.update_cell(next_row, 4, new_name)
                    st.success(f"'{new_name}' 추가 완료! (새로고침을 위해 메뉴를 다시 클릭하세요)")
            else:
                st.error("이름을 입력하세요.")

    # 3. 사용자 삭제
    with col_right:
        st.markdown("**사용자 삭제**")
        del_name = st.selectbox("삭제할 사용자 선택", ["선택하세요"] + names_list)
        if st.button("삭제하기"):
            if del_name != "선택하세요":
                # 지울 이름의 행 위치 찾기
                for i, cell_val in enumerate(col_d):
                    if cell_val.strip() == del_name:
                        # 해당 셀만 빈칸으로 덮어쓰기 (행 전체를 지우면 자재 데이터도 날아가므로)
                        sheet2.update_cell(i + 1, 4, "")
                        st.success(f"'{del_name}' 삭제 완료! (새로고침을 위해 메뉴를 다시 클릭하세요)")
                        break
