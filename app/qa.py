"""Questions & Answers parser and answer evaluation engine."""

from __future__ import annotations

import os
import re
from typing import Any

from app import db
from app.pron.engine import analyze


def parse_qa_note(text: str) -> list[dict[str, Any]]:
    """Parse a 'Questions & Answers' note text into structured question blocks."""
    lines = [line.strip() for line in text.splitlines()]
    q_indices = [
        i for i, line in enumerate(lines)
        if re.match(r"^(?:Question|Q):\s*", line, re.IGNORECASE)
    ]
    if not q_indices:
        return []

    questions = []
    # Track overall topic across blocks if provided as major section headers
    global_topic = "General"

    for idx_pos, q_idx in enumerate(q_indices):
        # 1. Extract Question text
        next_limit = q_indices[idx_pos + 1] if idx_pos + 1 < len(q_indices) else len(lines)
        q_text = re.sub(r"^(?:Question|Q):\s*", "", lines[q_idx], flags=re.IGNORECASE)
        kp_start_idx = -1

        for j in range(q_idx + 1, next_limit):
            if re.match(r"^(?:Key Points|Key Concepts(?: to Cover)?):\s*$", lines[j], re.IGNORECASE):
                kp_start_idx = j
                break
            elif lines[j]:
                q_text += " " + lines[j]

        # 2. Extract Key Points
        key_points: list[dict[str, str]] = []
        if kp_start_idx != -1:
            kp_end_idx = next_limit
            if idx_pos + 1 < len(q_indices):
                # Backtrack from next question through contiguous non-empty lines to find its title
                back_lines = []
                b_i = next_limit - 1
                while b_i > kp_start_idx and lines[b_i]:
                    back_lines.insert(0, b_i)
                    b_i -= 1
                if back_lines:
                    kp_end_idx = back_lines[0]

            curr_kp_title = ""
            curr_kp_desc = ""
            for k in range(kp_start_idx + 1, kp_end_idx):
                kp_line = lines[k]
                if not kp_line:
                    continue
                clean = re.sub(r"^[•\-\*\d\.\)]+\s*", "", kp_line)
                m_kp = re.match(r"^([^:]+):\s*(.*)$", clean)
                if m_kp and len(m_kp.group(1).split()) <= 10:
                    if curr_kp_title:
                        key_points.append({"title": curr_kp_title, "description": curr_kp_desc.strip()})
                    curr_kp_title = m_kp.group(1).strip()
                    curr_kp_desc = m_kp.group(2).strip()
                else:
                    if curr_kp_title:
                        curr_kp_desc += " " + clean
                    else:
                        curr_kp_title = clean[:40]
                        curr_kp_desc = clean
            if curr_kp_title:
                key_points.append({"title": curr_kp_title, "description": curr_kp_desc.strip()})

        # 3. Determine topic and subtopic
        # Look backwards from q_idx for non-empty header lines
        q_headers: list[str] = []
        b_k = q_idx - 1
        while b_k >= 0 and lines[b_k]:
            if lines[b_k] != "Questions & Answers":
                q_headers.insert(0, lines[b_k])
            b_k -= 1

        if len(q_headers) >= 2:
            global_topic = q_headers[-2]
            subtopic = q_headers[-1]
        elif len(q_headers) == 1:
            subtopic = q_headers[0]
            if global_topic == "General":
                global_topic = subtopic
        else:
            subtopic = f"Question {idx_pos + 1}"

        questions.append({
            "id": f"q_{idx_pos + 1}",
            "topic": global_topic,
            "subtopic": subtopic,
            "question": q_text.strip(),
            "key_points": key_points,
        })

    return questions


def get_qa_for_folder(folder: str | None = None) -> list[dict[str, Any]]:
    """Fetch and parse Q&A notes for the given folder or all folders."""
    sql = "SELECT id, folder, title, text FROM notes WHERE title LIKE '%Questions%'"
    args = []
    if folder:
        sql += " AND folder = ?"
        args.append(folder)

    with db.connect() as con:
        rows = [dict(r) for r in con.execute(sql, args)]

    all_questions = []
    for row in rows:
        parsed = parse_qa_note(row["text"])
        for q in parsed:
            q["folder"] = row["folder"]
            q["note_id"] = row["id"]
            q["note_title"] = row["title"]
            all_questions.append(q)

    return all_questions


# Common English stop words to ignore when doing keyword matching
STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "arent", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "cant", "cannot", "could", "couldnt", "did", "didnt", "do", "does", "doesnt",
    "doing", "dont", "down", "during", "each", "few", "for", "from", "further", "had", "hadnt",
    "has", "hasnt", "have", "havent", "having", "he", "hed", "hell", "hes", "her", "here",
    "heres", "hers", "herself", "him", "himself", "his", "how", "hows", "i", "id", "ill",
    "im", "ive", "if", "in", "into", "is", "isnt", "it", "its", "itself", "lets", "me", "more",
    "most", "mustnt", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shant",
    "she", "shed", "shell", "shes", "should", "shouldnt", "so", "some", "such", "than", "that",
    "thats", "the", "their", "theirs", "them", "themselves", "then", "there", "theres", "these",
    "they", "theyd", "theyll", "theyre", "theyve", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasnt", "we", "wed", "well", "were", "weve",
    "werent", "what", "whats", "when", "whens", "where", "wheres", "which", "while", "who",
    "whos", "whom", "why", "whys", "with", "wont", "would", "wouldnt", "you", "youd", "youll",
    "youre", "youve", "your", "yours", "yourself", "yourselves", "like", "also", "just", "make",
    "show", "walk", "through", "define", "what", "how", "why",
}


def _extract_keywords(text: str) -> set[str]:
    """Tokenize and stem/clean keywords from text."""
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
    return {w for w in words if w not in STOP_WORDS}


def evaluate_spoken_answer(question: dict[str, Any], spoken_text: str, duration_sec: float = 0) -> dict[str, Any]:
    """Evaluate a user's spoken answer against the key points of a question."""
    spoken_lower = spoken_text.lower()
    spoken_words = re.findall(r"\b\w+\b", spoken_lower)
    word_count = len(spoken_words)
    spoken_keywords = _extract_keywords(spoken_text)

    key_points = question.get("key_points", [])
    eval_points = []
    total_score = 0.0

    for kp in key_points:
        kp_title = kp.get("title", "")
        kp_desc = kp.get("description", "")
        title_keywords = _extract_keywords(kp_title)
        desc_keywords = _extract_keywords(kp_desc)
        all_kp_keywords = title_keywords | desc_keywords

        # Check matched keywords
        matched = [w for w in all_kp_keywords if w in spoken_keywords or w in spoken_lower]
        match_ratio = len(matched) / max(len(all_kp_keywords), 1)

        # Title match bonus (matching core terms from title is strong indicator)
        title_matched = [w for w in title_keywords if w in spoken_keywords or w in spoken_lower]
        has_title_match = len(title_matched) >= 1 if title_keywords else False

        if match_ratio >= 0.28 or (has_title_match and len(matched) >= 2):
            status = "covered"
            score = 1.0
        elif match_ratio >= 0.12 or len(matched) >= 1:
            status = "partial"
            score = 0.5
        else:
            status = "missing"
            score = 0.0

        total_score += score
        eval_points.append({
            "title": kp_title,
            "description": kp_desc,
            "status": status,
            "matched_terms": matched[:6],
        })

    coverage_pct = round((total_score / max(len(key_points), 1)) * 100) if key_points else 100

    # Speaking pace calculation
    wpm = 0
    pace_feedback = "Good response length."
    if duration_sec > 0:
        wpm = round((word_count / duration_sec) * 60)
        if wpm < 85:
            pace_feedback = f"Speaking pace is deliberate or measured ({wpm} WPM). Aim for a smooth flow between 110–140 WPM."
        elif wpm > 170:
            pace_feedback = f"Fast pace ({wpm} WPM). Try pausing between concepts for emphasis."
        else:
            pace_feedback = f"Great natural conversational pace ({wpm} WPM)."

    # Strengths and recommendations
    covered_cnt = sum(1 for p in eval_points if p["status"] == "covered")
    partial_cnt = sum(1 for p in eval_points if p["status"] == "partial")

    if coverage_pct >= 80:
        summary = f"Excellent! You covered {covered_cnt} of {len(key_points)} key concepts thoroughly."
    elif coverage_pct >= 50:
        summary = f"Good effort. You addressed {covered_cnt + partial_cnt} of {len(key_points)} concepts, but can expand on the details."
    else:
        summary = "Introductory answer. Try incorporating more specific economic concepts and examples from the key points."

    return {
        "coverage_pct": coverage_pct,
        "covered_count": covered_cnt,
        "total_points": len(key_points),
        "key_points": eval_points,
        "word_count": word_count,
        "duration_sec": round(duration_sec, 1),
        "wpm": wpm,
        "pace_feedback": pace_feedback,
        "summary": summary,
        "spoken_text": spoken_text,
    }


def get_shadowing_sentences(folder: str | None = None, note_id: str | None = None, limit: int = 40) -> list[dict[str, Any]]:
    """Extract practice sentences for shadowing from notes and vocabulary/pronunciation targets."""
    # First, gather target items with contexts
    item_sql = """
        SELECT i.id, i.note_id, i.folder, i.kind, i.text, i.context, n.title AS note_title
        FROM items i
        LEFT JOIN notes n ON n.id = i.note_id
        WHERE i.active = 1
    """
    args = []
    if folder:
        item_sql += " AND i.folder = ?"
        args.append(folder)
    if note_id:
        item_sql += " AND i.note_id = ?"
        args.append(note_id)

    item_sql += " ORDER BY i.created_at DESC LIMIT ?"
    args.append(limit)

    with db.connect() as con:
        item_rows = [dict(r) for r in con.execute(item_sql, args)]

    seen_contexts = set()
    sentences = []

    for r in item_rows:
        ctx = r.get("context", "").strip()
        if not ctx or ctx in seen_contexts:
            continue
        seen_contexts.add(ctx)

        # Clean context down to 1-2 clean sentences
        raw_sents = re.split(r"(?<=[.!?])\s+", ctx)
        target_sent = raw_sents[0].strip()
        for s in raw_sents:
            if r["text"].lower() in s.lower():
                target_sent = s.strip()
                break

        if len(target_sent) < 10 or len(target_sent) > 280:
            continue

        try:
            tokens = analyze(target_sent)
        except Exception:
            tokens = []

        sentences.append({
            "id": f"sent_{r['id']}",
            "text": target_sent,
            "target_word": r["text"],
            "kind": r["kind"],
            "folder": r["folder"],
            "note_id": r["note_id"],
            "note_title": r.get("note_title", "Note"),
            "tokens": tokens,
        })

    # If few sentences found, supplement with sentences directly from notes
    if len(sentences) < 10:
        notes_sql = "SELECT id, folder, title, text FROM notes WHERE title NOT LIKE '%Questions%'"
        n_args = []
        if folder:
            notes_sql += " AND folder = ?"
            n_args.append(folder)
        if note_id:
            notes_sql += " AND id = ?"
            n_args.append(note_id)

        with db.connect() as con:
            note_rows = [dict(r) for r in con.execute(notes_sql, n_args)]

        for nr in note_rows:
            paras = nr["text"].split("\n")
            for p in paras:
                p = p.strip()
                if not p or len(p) < 20 or len(p) > 200 or p.startswith("="):
                    continue
                sents = re.split(r"(?<=[.!?])\s+", p)
                for s in sents:
                    s = s.strip()
                    if 25 <= len(s) <= 150 and s not in seen_contexts:
                        seen_contexts.add(s)
                        try:
                            tokens = analyze(s)
                        except Exception:
                            tokens = []
                        sentences.append({
                            "id": f"sent_note_{len(sentences)}",
                            "text": s,
                            "target_word": "",
                            "kind": "general",
                            "folder": nr["folder"],
                            "note_id": nr["id"],
                            "note_title": nr["title"],
                            "tokens": tokens,
                        })
                        if len(sentences) >= limit:
                            break
                if len(sentences) >= limit:
                    break

    return sentences
