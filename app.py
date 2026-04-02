import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import requests
import re

# --- [1. 환경 설정] ---
# 클라우드 서버의 금고(secrets)에서 API 키를 꺼내옵니다.
API_KEY = st.secrets["YOUTUBE_API"]
youtube = build('youtube', 'v3', developerKey=API_KEY)

st.set_page_config(page_title="미국,일본 유튜브 분석기", layout="wide")

# --- [2. 핵심 로직 함수] ---
def translate_keyword(keyword, target_lang):
    try:
        return GoogleTranslator(source='ko', target=target_lang).translate(keyword)
    except: return keyword

def is_actually_shorts(video_id):
    try:
        url = f"https://www.youtube.com/shorts/{video_id}"
        response = requests.head(url, allow_redirects=False, timeout=3)
        return response.status_code == 200
    except: return True

def get_video_details(item, country):
    stats = item.get('statistics', {})
    views = int(stats.get('viewCount', 0))
    likes = int(stats.get('likeCount', 0))
    
    duration_str = item.get('contentDetails', {}).get('duration', 'PT0S')
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    total_seconds = (int(match.group(1) or 0) * 3600 + int(match.group(2) or 0) * 60 + int(match.group(3) or 0))
    
    is_short = total_seconds <= 61 and is_actually_shorts(item['id'])
    
    return {
        "국가": country,
        "포맷": "📱 쇼츠" if is_short else "📺 롱폼",
        "제목": item['snippet']['title'],
        "조회수": views,
        "좋아요": likes,
        "반응도": f"{round((likes/views)*100, 2) if views > 0 else 0}%",
        "날짜": item['snippet']['publishedAt'][:10],
        "썸네일": item['snippet']['thumbnails']['medium']['url'],
        "링크": f"https://www.youtube.com/watch?v={item['id']}"
    }

# --- [3. 사이드바 UI] ---
with st.sidebar:
    st.header("⚙️ 분석 설정")
    mode = st.radio("모드 선택", ["실시간 인기 차트", "키워드 정밀 검색"])
    target_format = st.selectbox("포맷 필터", ["전체", "📱 쇼츠만", "📺 롱폼만"])
    
    # [수정됨] 분석 기간을 선택 박스로 변경 (은혜님 요청사항 반영)
    period_options = {
        "1일": 1,
        "1주일": 7,
        "1개월": 30,
        "3개월": 90
        
    }
    selected_label = st.selectbox("업로드 시점 필터", list(period_options.keys()), index=1)
    days_limit = period_options[selected_label]
    
    keyword_ko = st.text_input("검색 키워드", value="동물")
    min_v = st.number_input("최소 조회수 기준", value=10000)
    
    # 버튼 너비를 가득 채우도록 설정
    start_btn = st.button("🚀 분석 시작", use_container_width=True)

# --- [4. 메인 화면 및 결과 출력] ---
st.title("📈 실시간 유튜브 순위 대시보드")

if start_btn:
    with st.spinner(f'{selected_label} 내의 데이터를 수집하고 있습니다...'):
        tasks = [{"region": "US", "lang": "en", "name": "미국"}, {"region": "JP", "lang": "ja", "name": "일본"}]
        final_data = []

        try:
            if mode == "실시간 인기 차트":
                for task in tasks:
                    req = youtube.videos().list(part="snippet,statistics,contentDetails", chart="mostPopular", regionCode=task['region'], maxResults=15).execute()
                    for item in req['items']:
                        final_data.append(get_video_details(item, task['name']))
            else:
                # 선택된 날짜만큼 과거 시간 계산
                after_date = (datetime.utcnow() - timedelta(days=days_limit)).isoformat() + 'Z'
                for task in tasks:
                    q_trans = translate_keyword(keyword_ko, task['lang'])
                    search = youtube.search().list(part="snippet", q=q_trans, regionCode=task['region'], publishedAfter=after_date, type="video", maxResults=25).execute()
                    v_ids = [i['id']['videoId'] for i in search['items']]
                    if v_ids:
                        details = youtube.videos().list(part="statistics,snippet,contentDetails", id=",".join(v_ids)).execute().get('items', [])
                        for item in details:
                            if int(item['statistics'].get('viewCount', 0)) >= min_v:
                                final_data.append(get_video_details(item, task['name']))

            if final_data:
                df = pd.DataFrame(final_data)
                if target_format == "📱 쇼츠만": df = df[df['포맷'] == "📱 쇼츠"]
                elif target_format == "📺 롱폼만": df = df[df['포맷'] == "📺 롱폼"]
                
                if not df.empty:
                    df = df.sort_values(by="조회수", ascending=False).reset_index(drop=True)
                    st.success(f"총 {len(df)}개의 글로벌 트렌드 영상을 찾았습니다!")
                    
                    html_content = """
<style>
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 20px; margin-top: 10px; }
.vid-card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.08); transition: 0.3s; color: #333; text-decoration: none; border-top: 4px solid #eee; display: flex; flex-direction: column; }
.vid-card:hover { transform: translateY(-5px); box-shadow: 0 8px 15px rgba(0,0,0,0.15); }
.shorts-card { border-top: 4px solid #EA4335; }
.card-info { padding: 15px; display: flex; flex-direction: column; flex-grow: 1; }
.rank-text { font-size: 16px; font-weight: 900; color: #EA4335; border-bottom: 2px dashed #eee; padding-bottom: 5px; margin-bottom: 10px; }
.vid-title { font-size: 14px; font-weight: bold; height: 40px; overflow: hidden; margin-bottom: 12px; color: #111; line-height: 1.4; }
.vid-stats { font-size: 12px; color: #666; margin-top: auto; }
.vid-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; color: white; margin-bottom: 8px; font-weight: bold; margin-right: 5px; }
.bg-us { background: #4285F4; } .bg-jp { background: #34A853; }
.bg-shorts { background: #EA4335; } .bg-long { background: #555; }
</style>
<div class='card-grid'>
"""
                    for idx, row in df.iterrows():
                        rank = idx + 1
                        badge_nat = "bg-us" if row['국가'] == "미국" else "bg-jp"
                        badge_fmt = "bg-shorts" if "쇼츠" in row['포맷'] else "bg-long"
                        card_class = "shorts-card" if "쇼츠" in row['포맷'] else ""
                        
                        html_content += f"""
<a href='{row['링크']}' target='_blank' class='vid-card {card_class}'>
    <img src='{row['썸네일']}' style='width:100%; aspect-ratio: 16/9; object-fit: cover;'>
    <div class='card-info'>
        <div class='rank-text'>🏆 {rank}위</div>
        <div>
            <span class='vid-badge {badge_nat}'>{row['국가']}</span>
            <span class='vid-badge {badge_fmt}'>{row['포맷']}</span>
        </div>
        <div class='vid-title'>{row['제목']}</div>
        <div class='vid-stats'>
            👁️ {row['조회수']:,} <br>
            ❤️ 좋아요: {row['좋아요']:,} ({row['반응도']}) <br>
            <span style='color:#aaa; font-size:11px;'>📅 {row['날짜']}</span>
        </div>
    </div>
</a>
"""
                    html_content += "</div>"
                    st.markdown(html_content, unsafe_allow_html=True)
                else:
                    st.warning("조건에 맞는 영상이 없습니다.")
            else:
                st.error("데이터 수집에 실패했습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")