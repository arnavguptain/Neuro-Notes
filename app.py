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
from gtts import gTTS

# 1. Structured Output Schema Definitions
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
    voiceover_script: str = Field(description="The explicit text-to-speech explanation script for this frame.")

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
    video_storyboard: List[VideoFrame] = Field(description="Exactly 3 sequential frames to compile into a core explainer presentation video.")
    sample_paper: List[SamplePaperQuestion] = Field(description="A full comprehensive 4-question mock exam paper covering the material.")

# 2. Page Config & Enhanced Premium UI Custom Styling
st.set_page_config(page_title="Neuro-Notes Studio Pro", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    /* Premium Study Dashboard Accents */
    .main-title { font-size: 3rem; font-weight: 800; color: #FF4B4B; margin-bottom: 5px; }
    .subtitle { color: #A3A8B4; font-size: 1.1rem; margin-bottom: 30px; }
    
    /* 3D Flipping Flashcard Cards */
    .flip-card { background-color: transparent; width: 100%; height: 200px; perspective: 1000px; margin-bottom: 25px; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; cursor: pointer; box-shadow: 0 8px 16px 0 rgba(0,0,0,0.3); border-radius: 12px; }
    .flip-card:hover .flip-card-inner { transform: rotateY(180deg); }
    .flip-card-front, .flip-card-back { position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 25px; border-radius: 12px; }
    .flip-card-front { background-color: #1E2028; color: #FFFFFF; border: 1px solid #3A3F50; font-size: 1.1rem; }
    .flip-card-back { background-color: #FF4B4B; color: white; transform: rotateY(180deg); font-size: 1.05rem; }
    
    /* Styled container formatting */
    .quiz-box { background-color: #1E2028; padding: 20px; border-radius: 10px; border: 1px solid #3A3F50; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🧠 Neuro-Notes Studio Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Convert classroom recording audio streams into interactive video presentations, custom maps, and structured notes blocks instantly.</div>', unsafe_allow_html=True)

# 3. Security Check
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.text_input("Enter Gemini API Key", type="password")

client = genai.Client(api_key=api_key) if api_key else None

if "quiz_answers" not in st.session_state: st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state: st.session_state.quiz_submitted = False

# 4. Audio Inputs Panel Sidebar
with st.sidebar:
    st.header("🎙️ Lecture Input Channel")
    input_method = st.radio("Choose Input Method:", ["🔴 Live Record Class", "📁 Upload Audio File"])
    audio_data = st.audio_input("Microphone") if input_method == "🔴 Live Record Class" else st.file_uploader("Upload Audio file resource", type=["mp3", "wav", "m4a", "ogg"])

# Helper function to dynamically compile slide canvas maps into a web-readable MP4 container format
def compile_web_video(storyboard):
    width, height = 800, 450
    fps = 24  # standard broadcast frequency mapping logic context
    
    temp_mp4 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    # 'mp4v' or alternative 'H264' fallback mapping tags for modern browsers
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    video_writer = cv2.VideoWriter(temp_mp4.name, fourcc, fps, (width, height))

    for frame in storyboard:
        # Create pure pillow display surface maps
        img = Image.new("RGB", (width, height), color=(26, 28, 36))
        draw = ImageDraw.Draw(img)
        
        # Simple graphic engine drawings (Draw clean rectangles and headers)
        draw.rectangle([(20, 20), (780, 430)], outline=(60, 64, 80), width=2)
        draw.text((50, 50), frame.slide_title.upper(), fill=(255, 75, 75))
        
        y_offset = 140
        for pt in frame.slide_text_points:
            draw.text((70, y_offset), f"- {pt}", fill=(230, 235, 245))
            y_offset += 60
            
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Let each presentation slide display clearly on timeline screen space for 4 full seconds
        for _ in range(fps * 4): 
            video_writer.write(cv_img)
            
    video_writer.release()
    return temp_mp4.name

# 5. Core Operational Flow Orchestrations
if client and audio_data:
    if st.sidebar.button("✨ Compile Complete Lecture Assets", type="primary"):
        with st.spinner("🧠 Processing lecture audio, synthesizing visual animation slides, and structuring academic notes..."):
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
                
                # Execute visual animation rendering matrices
                raw_video_output_path = compile_web_video(response.parsed.video_storyboard)
                
                # Convert compiled asset into base64 stream to force native browser playback bypass
                with open(raw_video_output_path, "rb") as f:
                    video_bytes = f.read()
                    st.session_state.video_base64 = base64.b64encode(video_bytes).decode("utf-8")
                
                os.remove(raw_video_output_path)
                st.success("All operational study assets compiled cleanly and successfully!")
                
            except Exception as e:
                st.error(f"Processing error encountered: {e}")
            finally:
                if os.path.exists(temp_file_path): os.remove(temp_file_path)

# 6. Interactive Multi-Tab Workspace Interface
if "study_data" in st.session_state:
    data = st.session_state.study_data
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📝 Textbook Notes", "🌿 Interactive Mind-Map", "🎬 Explainer Video", "🗂️ Flashcards", "🧠 Quiz Studio", "📄 Mock Exam Sheet"
    ])
    
    with tab1:
        st.subheader("📚 Rigorous Lecture Study Notes")
        clean_notes = data.detailed_notes.replace(r'\n', '\n')
        st.markdown(clean_notes)
        
    with tab2:
        st.subheader("🌿 Conceptual Hierarchy Roadmap Map")
        st.markdown(f"```mermaid\n{data.mindmap_mermaid}\n```")
        
    with tab3:
        st.subheader("🎬 Generated Concept Explainer Presentation Video")
        if "video_base64" in st.session_state:
            # Force standard HTML5 video injection directly matching compiled base64 data streams
            video_html = f"""
            <video width="100%" height="450" controls autoplay muted style="border-radius:12px; border:1px solid #3A3F50;">
                <source src="data:video/mp4;base64,{st.session_state.video_base64}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
            """
            st.markdown(video_html, unsafe_allow_html=True)
            
        st.markdown("### 📋 Presentation Script Breakdown Summary")
        for idx, frame in enumerate(data.video_storyboard):
            with st.expander(f"Slide Frame {idx+1}: {frame.slide_title}") as exp:
                st.write(f"**Visual Bullet Focus:** {', '.join(frame.slide_text_points)}")
                st.write(f"**Vocal Audio Script:** *\"{frame.voiceover_script}\"*")
                
    with tab4:
        st.subheader("🗂️ 3D Interactive Revision Cards")
        st.caption("Hover or tap your mouse pointer over the card component box layers below to flip them instantly.")
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
