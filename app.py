import streamlit as st
from streamlit_calendar import calendar
from datetime import datetime, timedelta, date
import os
import json

st.set_page_config(page_title="우리집 영수증 보관함", layout="centered")

# --- [1. 폴더 및 데이터 설정] ---
SAVE_DIR = "receipts_data"
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)

# 상세 정보(상호명, 금액)를 저장할 JSON 파일 경로
INFO_FILE = os.path.join(SAVE_DIR, "receipt_info.json")

def load_info():
    if os.path.exists(INFO_FILE):
        with open(INFO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_info(info_dict):
    with open(INFO_FILE, "w", encoding="utf-8") as f:
        json.dump(info_dict, f, ensure_ascii=False, indent=4)

# 점 표시용 이벤트 리스트 생성
def get_event_list():
    event_list = []
    receipt_info = load_info()
    # 정보가 등록된 날짜들을 순회하며 점 표시
    for date_key in receipt_info.keys():
        if receipt_info[date_key]: # 내역이 비어있지 않으면
            event_list.append({
                "title": "•", 
                "start": date_key, 
                "display": "background", 
                "color": "#ff4b4b"
            })
    return event_list

# --- [2. 상태 관리 및 날짜 통일] ---
# 오늘 날짜
today_str = str(date.today())

if "selected_date" not in st.session_state:
    st.session_state.selected_date = today_str

# 달력을 강제로 이동시키기 위한 key값 관리
if "calendar_key" not in st.session_state:
    st.session_state.calendar_key = 0

st.title("📂 영수증 보관함")

# --- [3. 버튼 통일: 오늘로 돌아가기] ---
if st.button("📍 오늘로 돌아가기",use_container_width=False):
    st.session_state.selected_date = today_str
    st.session_state.calendar_key += 1 # key를 바꿔서 달력을 새로 그리게 함
    st.rerun()

# --- [4. 달력 설정] ---

# --- [4. 달력 설정 및 그리기 (중복 제거 버전)] ---

# 1. 모든 이벤트 데이터 준비
dot_events = get_event_list() # 파일이 있는 날 점 표시
selected_day_event = [
    {
        "start": st.session_state.selected_date,
        "display": "background",
        "color": "#FFD1DC"  # 연분홍색 강조
    }
]

# 2. 옵션 통합
calendar_options = {
    "headerToolbar": {
        "left": "prev,next", 
        "center": "title", 
        "right": ""
    },
    "initialView": "dayGridMonth",
    "locale": "ko",
    
    # --- 크기 조절 핵심 ---
    "aspectRatio": 1.3,      # 숫자를 높여서 위아래 폭을 줄임
    "contentHeight": 350, #"auto", # 높이는 내용에 맞게 자동
    "handleWindowResize": True,
    
    # 날짜 숫자 크기가 너무 크면 줄여서 더 작게 보이게 할 수도 있습니다.
    "dayHeaderFormat": {"weekday": "narrow"}, 
}

# 3. 달력 그리기 (딱 한 번만 실행!)
# events 파라미터에 두 데이터를 합쳐서 넣습니다.
state = calendar(
    options=calendar_options, 
    events=dot_events + selected_day_event,
    key=f"cal_main_{st.session_state.calendar_key}" 
)

# 날짜 클릭 처리 (9시간 보정 포함)
if state.get("callback") == "dateClick":
    raw_date_str = state["dateClick"].get("date")
    if raw_date_str:
        clean_ts = raw_date_str.replace("T", " ").replace("Z", "")[:19]
        dt_obj = datetime.strptime(clean_ts, "%Y-%m-%d %H:%M:%S")
        kor_dt = dt_obj + timedelta(hours=9)
        new_date = kor_dt.strftime("%Y-%m-%d")
        
        if st.session_state.selected_date != new_date:
            st.session_state.selected_date = new_date
            st.rerun()



# --- [5. 하단 상세 내역 영역] ---
curr = st.session_state.selected_date
st.divider()
st.subheader(f"📅 {curr} 내역")

receipt_info = load_info()
day_data = receipt_info.get(curr, [])

if day_data:
    for idx, item in enumerate(day_data):
        # 정산 여부에 따라 배경색이나 느낌을 다르게 줄 수 있습니다.
        is_settled = item.get('settled', False)
        
        with st.container(border=True):
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # 1. 정산 체크박스
                # 체크박스를 누르면 즉시 JSON 파일에 저장됩니다.
                new_settled_val = st.checkbox(
                    f"**{item['store']}** ({item['price']}원)", 
                    value=is_settled, 
                    key=f"check_{curr}_{idx}"
                )
                if new_settled_val != is_settled:
                    day_data[idx]['settled'] = new_settled_val
                    receipt_info[curr] = day_data
                    save_info(receipt_info)
                    st.rerun()

            with col2:
                # 파일 보기 (Expander)
                show_img = st.button("👁️ 보기", key=f"view_{idx}")

            with col3:
                # 2. 삭제 확인 로직 (Popover 활용)
                # 버튼을 누르면 바로 삭제되지 않고 확인 창이 뜹니다.
                with st.popover("🗑️ 삭제"):
                    st.warning("정말 삭제하시겠습니까?")
                    if st.button("예, 삭제합니다", key=f"confirm_del_{idx}"):
                        # 파일 삭제
                        file_path = os.path.join(SAVE_DIR, curr, item['file_name'])
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        # 데이터 삭제
                        day_data.pop(idx)
                        receipt_info[curr] = day_data
                        save_info(receipt_info)
                        st.success("삭제되었습니다.")
                        st.rerun()
            
            # 사진 미리보기 영역 (보기 버튼을 눌렀을 때만 표시)
            if show_img:
                img_path = os.path.join(SAVE_DIR, curr, item['file_name'])
                st.image(img_path, use_container_width=True)
                with open(img_path, "rb") as f:
                    st.download_button("사진 저장", f, file_name=item['file_name'], key=f"down_{idx}")

else:
    st.info("등록된 내역이 없습니다.")
# --- [6. 업로드 영역: 상호명/금액 입력 포함] ---
with st.expander("➕ 새 영수증 등록하기"):
    with st.form("upload_form", clear_on_submit=True):
        u_file = st.file_uploader("영수증 파일 선택", accept_multiple_files=False)
        store_name = st.text_input("상호명 (예: 브로콜리 식당)")
        price = st.number_input("금액", min_value=0, step=100)
        
        submitted = st.form_submit_button("저장하기")
        if submitted:
            if u_file and store_name:
                target_path = os.path.join(SAVE_DIR, curr)
                if not os.path.exists(target_path):
                    os.makedirs(target_path)
                
                # 파일 저장
                with open(os.path.join(target_path, u_file.name), "wb") as f:
                    f.write(u_file.getbuffer())
                
                # 정보 저장 (JSON)
                # 업로드 로직 중 new_item 부분 수정
                new_item = {
                    "file_name": u_file.name,
                    "store": store_name,
                    "price": format(price, ','),
                    "settled": False,  # 처음 올릴 때는 정산 미완료 상태
                    "upload_at": str(datetime.now())
                }
                if curr not in receipt_info:
                    receipt_info[curr] = []
                receipt_info[curr].append(new_item)
                save_info(receipt_info)
                
                st.success("등록 완료!")
                st.rerun()
            else:
                st.warning("파일과 상호명을 모두 입력해주세요.")
