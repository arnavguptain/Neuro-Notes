import streamlit as st
import os
import tempfile
import cv2
import numpy as np
import base64
from PIL import Image, ImageDraw
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

# 1. Schema Layout Constraints
class Flashcard(BaseModel):
    front: str = Field(description="The conceptual question or definition term.")
    back: str = Field(description="The answer or detailed explanation.")

class QuizItem(BaseModel):
    question: str = Field(description="The multiple choice question text.")
    options: List[str] = Field(description="Exactly 4 realistic option choices.")
    correct_index: int = Field(description="The index (0-3) of the correct option.")

class VideoFrame(BaseModel):
    slide_title: str = Field(description="A short keyword title representing this frame topic.")
    slide_text_points: List[str] = Field(description="3 clear bullet points summarizing the core concept visually.")

class SamplePaperQuestion(BaseModel):
    section: str = Field(description="Section name (e.g., Section A, Section B)")
    marks: int = Field(description="Weight of the question (e.g., 5, 10)")
    question_text: str = Field(description="The academic exam question.")
    marking_scheme: str = Field(description="Detailed grading points required for full marks.")

class StudyGuideSchema(BaseModel):
    detailed_notes: str = Field(description="In-depth, textbook-quality academic notes. Use standard markdown structure with clean headers (##), bold terms, lists, and proper paragraphs.")
    mindmap_mermaid: str = Field(description="A valid, well-structured Mermaid.js syntax flowchart using graph TD.")
    flashcards: List[Flashcard] = Field(description="A list of 4 concept flashcards.")
    quiz: List[QuizItem] = Field(description="A list of 3 diagnostic multiple-choice questions.")
    video_storyboard: List[VideoFrame] = Field(description="Exactly 4 sequential animation frames to build a continuous explainer video.")
    sample_paper: List[SamplePaperQuestion] = Field(description="A full comprehensive 4-question mock exam paper covering the material.")

# 2. Page Configuration & Custom Styling
st.set_page_config(page_title="Neuro-Notes Studio Pro", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .main-title { font-size: 3rem; font-weight: 800; color: #FF4B4B; margin-bottom: 5px; }
    .subtitle { color: #A3A8B4; font-size: 1.1rem; margin-bottom: 30px; }
    .flip-card { background-color: transparent; width: 100%; height: 200px; perspective: 1000px; margin-bottom: 25px; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; cursor: pointer; box-shadow: 0 8px 16px 0 rgba(0,0,0,0.3); border-radius: 12px; }
    .flip-card:hover .flip-card-inner { transform: rotateY(180deg); }
    .flip-card-front, .flip-card-back { position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 25px; border-radius: 12px; }
    .flip-card-front { background-color: #1E2028; color: #FFFFFF; border: 1px solid #3A3F50; font-size: 1.1rem; }
    .flip-card-back { background-color: #FF4B4B; color: white; transform: rotateY(180deg); font-size: 1.05rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🧠 Neuro-Notes Studio Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Convert audio streams into premium animation tracks, custom hierarchical mind maps, and structured study notes instantly.</div>', unsafe_allow_html=True)

# 3. Security Check
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.text_input("Enter Gemini API Key", type="password")

client = genai.Client(api_key=api_key) if api_key else None

if "quiz_answers" not in st.session_state: st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state: st.session_state.quiz_submitted = False

# 4. Input Configuration Channel Selector
with st.sidebar:
    st.header("🎙️ Lecture Input Channel")
    input_method = st.radio("Choose Input Method:", ["🔴 Live Record Class", "📁 Upload Audio File"])
    audio_data = st.audio_input("Microphone") if input_method == "🔴 Live Record Class" else st.file_uploader("Upload Audio Resource File", type=["mp3", "wav", "m4a", "ogg"])

# Helper functions to convert animation structures into browser-supported video byte streams
def render_animation_video(storyboard):
    width, height = 960, 540
    fps = 10
    
    temp_avi = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    # Using specific codec matrix definitions compatible natively with downstream browser wrappers
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    
    # Fallback to alternative mp4v mapping container configurations if specific environment lacks system frameworks
    video_writer = cv2.VideoWriter(temp_avi.name, fourcc, fps, (width, height))
    if not video_writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(temp_avi.name, fourcc, fps, (width, height))

    for frame_idx, frame in enumerate(storyboard):
        # Frame transitions: Compile individual visual scene slides dynamically
        img = Image.new("RGB", (width, height), color=(22, 24, 30))
        draw = ImageDraw.Draw(img)
        
        # UI Accent Design: Smooth layout frames
        draw.rectangle([(25, 25), (935, 515)], outline=(46, 50, 62), width=3)
        draw.rectangle([(35, 35), (925, 85)], fill=(34, 38, 48))
        
        # Text Header placement matrices
        draw.text((50, 48), f"SCENE {frame_idx + 1}: {frame.slide_title.upper()}", fill=(255, 75, 75))
        
        y_offset = 160
        for pt in frame.slide_text_points:
            draw.text((70, y_offset), f"• {pt}", fill=(230, 235, 245))
            y_offset += 75
            
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Display each individual animation board slide on frame for exactly 5 seconds
        for _ in range(fps * 5):
            video_writer.write(cv_img)
            
    video_writer.release()
    return temp_avi.name

# 5. Core Operational Flow Orchestration Engine
if client and audio_data:
    if st.sidebar.button("✨ Compile Complete Lecture Assets", type="primary"):
        with st.spinner("🧠 Synthesizing complete textbook notes, hierarchy roadmaps, and running explainer animations..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data.read() if hasattr(audio_data, 'read') else audio_data.getvalue())
                temp_file_path = temp_file.name
            
            try:
                audio_media = client.files.upload(file=temp_file_path)
                
                prompt = (
                    "Process this classroom lecture recording completely. Generate comprehensive, cleanly formatted, "
                    "textbook-quality academic notes inside the detailed_notes schema parameter, ensuring clean markdown structure. "
                    "Create complete Mermaid roadmap trees, concept flashcards, mock sample exams, and exact presentation slide frames."
                )
                
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=[prompt, audio_media],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=StudyGuideSchema,
                        temperature=0.2
                    )
                )
                
                client.files.delete(name=audio_media.name)
                st.session_state.study_data = response.parsed
                st.session_state.quiz_submitted = False
                st.session_state.quiz_answers = {}
                
                # Dynamic rendering compilation pipeline trigger
                raw_video_output_path = render_animation_video(response.parsed.video_storyboard)
                
                with open(raw_video_output_path, "rb") as f:
                    video_bytes = f.read()
                    st.session_state.video_base64 = base64.b64encode(video_bytes).decode("utf-8")
                
                os.remove(raw_video_output_path)
                st.success("All dynamic operational study assets compiled cleanly and successfully!")
                
            except Exception as e:
                st.error(f"Processing error encountered: {e}")
            finally:
                if os.path.exists(temp_file_path): os.remove(temp_file_path)

# 6. Interactive Multi-Tab Study Dashboard Interface
if "study_data" in st.session_state:
    data = st.session_state.study_data
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🎬 Animated Explainer Video", "📝 Textbook Notes", "🌿 Interactive Mind-Map", "🗂️ Flashcards", "🧠 Quiz Studio", "📄 Mock Exam Sheet"
    ])
    
    with tab1:
        st.subheader("🎬 AI Generated Animation Explainer Video")
        if "video_base64" in st.session_state:
            video_html = f"""
            <div style="max-width: 960px; margin: 0 auto;">
                <video width="100%" height="auto" controls autoplay muted style="border-radius:12px; border:2px solid #2e323e; box-shadow: 0 12px 24px rgba(0,0,0,0.5);">
                    <source src="data:video/mp4;base64,{st.session_state.video_base64}" type="video/mp4">
                    Your browser does not support playing this animation file.
                </video>
            </div>
            """
            st.markdown(video_html, unsafe_allow_html=True)
        else:
            st.error("Video tracking asset context could not be read cleanly. Please recompile the pipeline inputs.")
        
    with tab2:
        st.subheader("📚 Rigorous Lecture Study Notes")
        clean_notes = data.detailed_notes.replace(r'\n', '\n')
        st.markdown(clean_notes)
        
    with tab3:
        st.subheader("🌿 Conceptual Hierarchy Roadmap Map")
        st.markdown(f"```mermaid\n{data.mindmap_mermaid}\n```")
        
    with tab4:
        st.subheader("🗂️ 3D Interactive Revision Cards")
        cols = st.columns(2)
        for idx, card in enumerate(data.flashcards):
            with cols[idx % 2]:
                st.markdown(f"""
                <div class="flip-card">
                    <div class="flip-card-inner">
                        <div class="flip-card-front">
                            <span style="color:#FF4B4B; font-weight:bold; margin-bottom:10px;">QUESTION</span>
                            <strong>{card.front}</strong>
                        </div>
                        <div class="flip-card-back">
                            <span style="font-weight:bold; margin-bottom:10px;">EXPLANATION DETAILED ANSWER</span>
                            <span>{card.back}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
    with tab5:
        st.subheader("🧠 Concept Retention Assessment Quiz")
        for idx, item in enumerate(data.quiz):
            st.markdown(f"**Question {idx+1}:** {item.question}")
            st.session_state.quiz_answers[idx] = st.radio(
                f"Selection Options Choice Matrix Q{idx+1}:", options=item.options, key=f"q_{idx}", label_visibility="collapsed"
            )
            st.write("")
            
        if st.button("Submit Answers Evaluation"): st.session_state.quiz_submitted = True
            
        if st.session_state.quiz_submitted:
            score = 0
            st.markdown("---")
            for idx, item in enumerate(data.quiz):
                user = st.session_state.quiz_answers.get(idx)
                correct = item.options[item.correct_index]
                if user == correct:
                    score += 1
                    st.success(f"✔️ **Question {idx+1}: Correct!** You selected: {user}")
                else:
                    st.error(f"❌ **Question {idx+1}: Incorrect.** You selected: {user} | **Correct Answer:** {correct}")
            st.metric("Final Cumulative Assessment Score", f"{score} / {len(data.quiz)}")
            
    with tab6:
        st.subheader("📄 Simulated Term Mock Examination Paper")
        for idx, q in enumerate(data.sample_paper):
            st.markdown(f"### {q.section}")
            st.markdown(f"**Question {idx+1} ({q.marks} Marks):** {q.question_text}")
            with st.expander("🔍 Show Scoring Criteria Blueprint"):
                st.write(q.marking_scheme)
            st.markdown("---")
            
elif not api_key:
    st.warning("Please configure your Gemini API token to begin processing audio files.")
else:
    st.info("Record a live classroom discussion via microphone or upload an audio clip to start generating.")
