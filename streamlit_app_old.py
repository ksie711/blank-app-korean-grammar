import streamlit as st
import pandas as pd
import sqlite3
import uuid
from datetime import datetime
import random
import re

# =========================
# 기본 설정
# =========================
st.set_page_config(page_title="한국어 문제 자동 출제/풀이", layout="wide")
st.title("📘 한국어 문제 자동 출제/풀이 (TOPIK 1~6급)")

PDF_PATH = "한국어교수학습샘터-문법·표현 내용 검색-거니와 (1).pdf"
XLSX_PATH = "한국어능력시험(TOPIK) 1급~6급(초급~고급) 급수별 어휘목록 (1).xlsx"
DB_PATH = "app.db"

# =========================
# DB
# =========================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id TEXT,
        question TEXT,
        answer TEXT,
        student_answer TEXT,
        correct INTEGER,
        created_at TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# =========================
# 데이터 로드
# =========================
@st.cache_data
def load_vocab():
    df = pd.read_excel(XLSX_PATH)
    df = df.astype(str)
    vocab = {}
    for i in range(1, 7):
        vocab[i] = df[df.iloc[:,1].str.contains(str(i))].iloc[:,0].tolist()
    return vocab

try:
    vocab_by_level = load_vocab()
except:
    st.error("❌ TOPIK 어휘 엑셀을 읽지 못했습니다. 파일이 같은 폴더에 있는지 확인하세요.")
    st.stop()

# =========================
# 문제 생성
# =========================
def make_questions(level: int):
    words = vocab_by_level[level]
    if len(words) < 5:
        return []

    questions = []
    chosen = random.sample(words, 5)

    for w in chosen:
        q = f"다음 빈칸에 알맞은 단어를 쓰세요.\n나는 ___을/를 좋아합니다."
        questions.append({
            "id": str(uuid.uuid4()),
            "question": q,
            "answer": w,
            "explanation": f"정답은 '{w}'입니다."
        })
    return questions

# =========================
# UI
# =========================
mode = st.sidebar.radio("모드 선택", ["교사", "학생"])

if mode == "교사":
    st.subheader("🧑‍🏫 교사 모드")

    level = st.selectbox(
        "급수 선택 (TOPIK)",
        [1, 2, 3, 4, 5, 6],
        format_func=lambda x: f"{x}급"
    )

    st.caption(f"📌 현재 {level}급 어휘 수: {len(vocab_by_level[level])}개")

    if st.button("✅ 문제 5개 생성"):
        qs = make_questions(level)
        if not qs:
            st.error("문제를 만들 수 없습니다. 어휘 수가 너무 적습니다.")
        else:
            st.session_state["questions"] = qs
            st.success("문제 생성 완료!")

    if "questions" in st.session_state:
        st.markdown("### 📄 생성된 문제")
        for i, q in enumerate(st.session_state["questions"], 1):
            st.write(f"**{i}.** {q['question']}")
            st.caption(f"정답: {q['answer']}")

elif mode == "학생":
    st.subheader("🧑‍🎓 학생 모드")

    if "questions" not in st.session_state:
        st.info("교사가 먼저 문제를 생성해야 합니다.")
        st.stop()

    answers = []
    for i, q in enumerate(st.session_state["questions"], 1):
        ans = st.text_input(f"{i}. {q['question']}", key=q["id"])
        answers.append((q, ans))

    if st.button("📤 제출"):
        score = 0
        conn = get_conn()
        cur = conn.cursor()

        for q, ans in answers:
            correct = int(ans.strip() == q["answer"])
            score += correct
            cur.execute(
                "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?)",
                (
                    q["id"],
                    q["question"],
                    q["answer"],
                    ans,
                    correct,
                    datetime.utcnow().isoformat()
                )
            )

        conn.commit()
        conn.close()

        st.success(f"총 {score}/5 정답입니다!")

        for q, ans in answers:
            if ans.strip() != q["answer"]:
                st.error(f"❌ 오답: {q['answer']}")
            else:
                st.success("✅ 정답")


