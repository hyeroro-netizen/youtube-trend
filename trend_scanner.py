import os
import sys
import re
import requests # 웹페이지 통신(URL 테스트)을 위한 모듈 추가

# [경로 강제 설정] 3.13 버전 Tcl/Tk
try:
    base_path = r"C:\Users\Administrator\AppData\Local\Programs\Python\Python313\tcl"
    os.environ['TCL_LIBRARY'] = os.path.join(base_path, 'tcl8.6')
    os.environ['TK_LIBRARY'] = os.path.join(base_path, 'tk8.6')
except Exception as e:
    pass

import pandas as pd
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator
import webbrowser
import tkinter as tk
from tkinter import messagebox

# --- [1. 환경 설정] ---
API_KEY = "AIzaSyDbii4boc0tuFzQviWM9FVwE2JBZjoWp9w"
youtube = build('youtube', 'v3', developerKey=API_KEY)

# --- [2. 핵심 로직 함수] ---

def translate_keyword(keyword, target_lang):
    try:
        return GoogleTranslator(source='ko', target=target_lang).translate(keyword)
    except:
        return keyword

def is_actually_shorts(video_id):
    """URL 리다이렉트 테스트로 진짜 쇼츠인지 100% 검증하는 함수"""
    try:
        # 유튜브 쇼츠 전용 주소로 찔러보기
        url = f"https://www.youtube.com/shorts/{video_id}"
        # 유튜브 서버에 요청 (리다이렉트 허용 안함)
        response = requests.head(url, allow_redirects=False, timeout=3)
        
        # 200(정상)이 뜨면 진짜 쇼츠, 303(다른 곳으로 보냄)이 뜨면 일반 롱폼 영상임
        if response.status_code == 200:
            return True
        else:
            return False
    except:
        return True # 오류 시 기본값 처리

def format_data(item, country, type_label):
    stats = item.get('statistics', {})
    views = int(stats.get('viewCount', 0))
    likes = int(stats.get('likeCount', 0))
    video_id = item['id']
    
    # 1차 필터: 영상 길이 계산
    duration_str = item.get('contentDetails', {}).get('duration', 'PT0S')
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    hours = int(match.group(1)) if match and match.group(1) else 0
    minutes = int(match.group(2)) if match and match.group(2) else 0
    seconds = int(match.group(3)) if match and match.group(3) else 0
    total_seconds = hours * 3600 + minutes * 60 + seconds
    
    # 2차 필터: 61초 이하일 경우에만 URL 테스트 진행 (속도 최적화)
    if total_seconds <= 61:
        if is_actually_shorts(video_id):
            video_format = "📱 쇼츠"
        else:
            video_format = "📺 롱폼 (가로형 짧은 영상)"
    else:
        video_format = "📺 롱폼"
    
    return {
        "국가": country,
        "유형": type_label,
        "포맷": video_format,
        "제목": item['snippet']['title'],
        "조회수": f"{views:,}",
        "반응도": f"{round((likes/views)*100, 2) if views > 0 else 0}%",
        "링크": f"https://www.youtube.com/watch?v={video_id}",
        "썸네일": item['snippet']['thumbnails']['medium']['url'],
        "날짜": item['snippet']['publishedAt'][:10]
    }

def save_to_html(data):
    # 조회수 기준 내림차순 정렬
    data = sorted(data, key=lambda x: int(x['조회수'].replace(',', '')), reverse=True)
    
    # 순위 매기기
    for i, d in enumerate(data):
        d['순위'] = i + 1
        
    html_content = f"""
    <html><head><meta charset='UTF-8'><title>은혜의 벤치마킹 리포트</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; background: #f4f7f6; padding: 30px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 30px; }}
        .card {{ background: white; border-radius: 15px; overflow: hidden; box-shadow: 0 10px 20px rgba(0,0,0,0.05); transition: 0.3s; position: relative; border-top: 4px solid #fff; }}
        .card:hover {{ transform: translateY(-5px); box-shadow: 0 15px 30px rgba(0,0,0,0.15); }}
        .shorts-card {{ border-top: 4px solid #ff0000; }} /* 쇼츠는 상단 빨간 포인트 */
        .info {{ padding: 20px; }}
        .rank {{ font-size: 18px; font-weight: 900; color: #EA4335; margin-bottom: 10px; border-bottom: 2px dashed #eee; padding-bottom: 8px; }}
        .title {{ font-size: 15px; font-weight: bold; height: 44px; overflow: hidden; margin-bottom: 12px; color: #333; }}
        .stats {{ font-size: 13px; color: #666; font-weight: 500; }}
        .date {{ font-size: 11px; color: #bbb; margin-top: 10px; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 11px; color: white; margin-bottom: 10px; font-weight: bold; margin-right: 5px; }}
        .us {{ background: #4285F4; }} .jp {{ background: #34A853; }} 
        .format-shorts {{ background: #EA4335; }} .format-long {{ background: #555; }}
        a {{ text-decoration: none; color: inherit; }}
    </style></head><body>
    <div class='header'>
        <h1>📈 글로벌 유튜브 벤치마킹 리포트 (포맷 정밀분석 적용)</h1>
        <p>생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
    <div class='grid'>
    """
    for d in data:
        badge_class = "us" if d['국가'] == "미국" else "jp"
        format_badge = "format-shorts" if "쇼츠" in d['포맷'] else "format-long"
        card_class = "shorts-card" if "쇼츠" in d['포맷'] else ""
        
        html_content += f"""
        <a href='{d['링크']}' target='_blank'><div class='card {card_class}'>
            <img src='{d['썸네일']}' style='width:100%'>
            <div class='info'>
                <div class='rank'>🏆 {d['순위']}위</div>
                <span class='badge {badge_class}'>{d['국가']}</span>
                <span class='badge {format_badge}'>{d['포맷']}</span>
                <div class='title'>{d['제목']}</div>
                <div class='stats'>👁️ {d['조회수']}  |  ❤️ {d['반응도']}</div>
                <div class='date'>📅 {d['날짜']} 업로드</div>
            </div>
        </div></a>"""
    html_content += "</div></body></html>"
    
    file_path = "dashboard.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    webbrowser.open(file_path)

# --- [3. GUI 및 실행 함수] ---

def start_analysis():
    mode = var_mode.get()
    keyword_ko = ent_keyword.get()
    try:
        days_limit = int(ent_days.get())
        min_views = int(ent_views.get())
    except ValueError:
        messagebox.showerror("입력 오류", "기간과 조회수는 숫자만 입력해주세요!")
        return

    status_label.config(text="⏳ 정밀 분석 중... (쇼츠 판독 중이라 5~10초 걸립니다)", fg="#0056b3")
    root.update()

    tasks = [{"region": "US", "lang": "en", "name": "미국"}, {"region": "JP", "lang": "ja", "name": "일본"}]
    final_data = []

    try:
        if mode == 1:
            for task in tasks:
                req = youtube.videos().list(part="snippet,statistics,contentDetails", chart="mostPopular", regionCode=task['region'], maxResults=12).execute()
                for item in req['items']:
                    final_data.append(format_data(item, task['name'], "인기차트"))
        else:
            if not keyword_ko:
                messagebox.showwarning("입력 필요", "검색할 키워드를 입력해주세요!")
                return
            
            published_after = (datetime.utcnow() - timedelta(days=days_limit)).isoformat() + 'Z'
            for task in tasks:
                translated_q = translate_keyword(keyword_ko, task['lang'])
                search_res = youtube.search().list(
                    part="snippet", q=translated_q, regionCode=task['region'],
                    publishedAfter=published_after, type="video", maxResults=20
                ).execute()
                
                v_ids = [i['id']['videoId'] for i in search_res['items']]
                if v_ids:
                    details = youtube.videos().list(part="statistics,snippet,contentDetails", id=",".join(v_ids)).execute().get('items', [])
                    for item in details:
                        if int(item['statistics'].get('viewCount', 0)) >= min_views:
                            final_data.append(format_data(item, task['name'], f"검색: {keyword_ko}"))

        if final_data:
            save_to_html(final_data)
            status_label.config(text="✅ 분석 완료! 대시보드가 열렸습니다.", fg="#28a745")
        else:
            status_label.config(text="❌ 결과가 없습니다. 조건을 낮춰보세요.", fg="#dc3545")
            
    except Exception as e:
        messagebox.showerror("오류 발생", f"상세 내용: {e}")
        status_label.config(text="❌ 오류 발생", fg="#dc3545")

# --- [4. GUI 화면 구성] ---

root = tk.Tk()
root.title("은혜의 유튜브 벤치마커 v8.0 (Pro)")
root.geometry("450x550")
root.configure(padx=20, pady=20)

tk.Label(root, text="🎥 유튜브 글로벌 벤치마커", font=("Malgun Gothic", 18, "bold"), fg="#EA4335").pack(pady=20)

var_mode = tk.IntVar(value=1)
frame_mode = tk.LabelFrame(root, text="1. 분석 모드 선택", padx=10, pady=10)
frame_mode.pack(fill="x", pady=10)
tk.Radiobutton(frame_mode, text="국가별 인기 차트", variable=var_mode, value=1).pack(side="left", padx=10)
tk.Radiobutton(frame_mode, text="키워드 정밀 검색", variable=var_mode, value=2).pack(side="left", padx=10)

frame_input = tk.LabelFrame(root, text="2. 세부 설정", padx=10, pady=10)
frame_input.pack(fill="x", pady=10)

tk.Label(frame_input, text="검색 키워드:").grid(row=0, column=0, sticky="w")
ent_keyword = tk.Entry(frame_input, width=30)
ent_keyword.grid(row=0, column=1, pady=5)

tk.Label(frame_input, text="분석 기간 (최근 며칠?):").grid(row=1, column=0, sticky="w")
ent_days = tk.Entry(frame_input, width=10)
ent_days.insert(0, "7")
ent_days.grid(row=1, column=1, sticky="w", pady=5)

tk.Label(frame_input, text="최소 조회수 필터:").grid(row=2, column=0, sticky="w")
ent_views = tk.Entry(frame_input, width=15)
ent_views.insert(0, "10000")
ent_views.grid(row=2, column=1, sticky="w", pady=5)

btn_run = tk.Button(root, text="분석 시작하기", command=start_analysis, bg="#EA4335", fg="white", font=("Malgun Gothic", 12, "bold"), height=2)
btn_run.pack(fill="x", pady=30)

status_label = tk.Label(root, text="준비 완료", font=("Malgun Gothic", 10))
status_label.pack()

root.mainloop()