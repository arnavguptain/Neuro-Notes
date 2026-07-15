import streamlit as st
import os
import tempfile
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
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
    detailed_notes: str = Field(description="In-depth, textbook-quality academic notes. Do not include raw string literals like \\n. Use standard markdown structure with clean headers (##), bold terms, lists, and proper paragraphs.")
    mindmap_mermaid: str = Field(description="A valid, well-structured Mermaid.js syntax flowchart using graph TD.")
    flashcards: List[Flashcard] = Field(description="A list of 4 concept flashcards.")
    quiz: List[QuizItem] = Field(description="A list of 3 diagnostic multiple-choice questions.")
    video_storyboard: List[VideoFrame] = Field(description="Exactly 3 sequential frames to compile into a core explainer presentation video.")
    sample_paper: List[SamplePaperQuestion] = Field(description="A full comprehensive 4-question mock exam paper covering the material.")

# 2. Page Config
st.set_page_config(page_title="Neuro-Notes Studio Pro", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .flip-card { background-color: transparent; width: 100%; height: 180px; perspective: 1000px; margin-bottom: 20px; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; cursor: pointer; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); border-radius: 10px; }
    .flip-card:hover .flip-card-inner { transform: rotateY(180deg); }
    .flip-card-front, .flip-card-back { position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; display: flex; align-items: center; justify-content: center; padding: 20px; border-radius: 10px; }
    .flip-card-front { background-color: #262730; color: white; border: 1px solid #464855; }
    .flip-card-back { background-color: #FF4B4B; color: white; transform: rotateY(180deg); }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Neuro-Notes AI Classroom Studio Pro")
st.caption("Generate rigorous structured study assets, beautiful notes, and animated explainer videos natively.")

# 3. Key Validation
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.text_input("Enter Gemini API Key", type="password")

client = genai.Client(api_key=api_key) if api_key else None

if "quiz_answers" not in st.session_state: st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state: st.session_state.quiz_submitted = False

# 4. Audio Controls
with st.sidebar:
    st.header("🎙️ Classroom Audio Input")
    input_method = st.radio("Choose Input Method:", ["🔴 Live Record Class", "📁 Upload Audio File"])
    audio_data = st.audio_input("Microphone") if input_method == "🔴 Live Record Class" else st.file_uploader("Upload Audio", type=["mp3", "wav", "m4a", "ogg"])

# Helper function to dynamically compile slide visuals into real video
def compile_video_file(storyboard):
    width, height = 800, 450
    fps = 2
    temp_avi = tempfile.NamedTemporaryFile(delete=False, suffix=".avi")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    video_writer = cv2.VideoWriter(temp_avi.name, fourcc, fps, (width, height))

    for frame in storyboard:
        # Create a blank digital canvas slide
        img = Image.new("RGB", (width, height), color=(30, 30, 36))
        draw = ImageDraw.Draw(img)
        
        # Write slide structural texts
        draw.text((40, 40), frame.slide_title.upper(), fill=(255, 75, 75))
        y_offset = 120
        for pt in frame.slide_text_points:
            draw.text((60, y_offset), f"• {pt}", fill=(240, 240, 240))
            y_offset += 50
            
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        
        # Write frames representing slide exposure timing duration
        for _ in range(fps * 4): 
            video_writer.write(cv_img)
            
    video_writer.release()
    return temp_avi.name

# 5. Pipeline Orchestration
if client and audio_data:
    if st.sidebar.button("✨ Compile Complete Lecture Assets", type="primary"):
        with st.spinner("🧠 Analyzing lecture segments, mapping concepts, and generating full study files..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data.read() if hasattr(audio_data, 'read') else audio_data.getvalue())
                temp_file_path = temp_file.name
            
            try:
                audio_media = client.files.upload(file=temp_file_path)
                
                prompt = (
                    "Process this classroom lecture recording completely. Generate comprehensive, cleanly formatted, "
                    "textbook-quality academic notes inside the detailed_notes schema parameter, ensuring clean markdown structure. "
                    "Do not inject raw string literal text formatting markers. Create complete Mermaid roadmap trees, concept flashcards, "
                    "mock sample exams, and exact presentation slide frames."
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
                
                # Compile frames into a real viewable video presentation file instantly
                st.session_state.video_path = compile_video_file(response.parsed.video_storyboard)
                st.success("All assets generated successfully!")
                
            except Exception as e:
                st.error(f"Processing error: {e}")
            finally:
                if os.path.exists(temp_file_path): os.remove(temp_file_path)

# 6. Dynamic Frontend
if "study_data" in st.session_state:
    data = st.session_state.study_data
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📝 Comprehensive Notes", "🌿 Interactive Mind-Map", "🎬 Explainer Video", "🗂️ Flashcards", "🧠 Quiz", "📄 Mock Exam Paper"
    ])
    
    with tab1:
        st.header("Comprehensive Academic Lecture Notes")
        # Ensure clean text replacement formatting on any leftover string data artifacts
        clean_notes = data.detailed_notes.replace(r'\n', '\n')
        st.markdown(clean_notes)
        
    with tab2:
        st.header("Visual Concept Mind-Map")
        st.markdown(f"```mermaid\n{data.mindmap_mermaid}\n```")
        
    with tab3:
        st.header("AI Visual Video Explainer Reel")
        if "video_path" in st.session_state and os.path.exists(st.session_state.video_path):
            st.video(st.session_state.video_path)
            
        st.subheader("Storyboard Script Breakdown")
        for idx, frame in enumerate(data.video_storyboard):
            st.markdown(f"**Slide {idx+1}: {frame.slide_title}**")
            st.caption(f"Voiceover Text: {frame.voiceover_script}")
            
    with tab4:
        st.header("Concept Flashcards")
        cols = st.columns(2)
        for idx, card in enumerate(data.flashcards):
            with cols[idx % 2]:
                st.markdown(f"""
                <div class="flip-card">
                    <div class="flip-card-inner">
                        <div class="flip-card-front"><strong>{card.front}</strong></div>
                        <div class="flip-card-back"><span>{card.back}</span></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
    with tab5:
        st.header("Diagnostic Quiz")
        for idx, item in enumerate(data.quiz):
            st.markdown(f"**Q{idx+1}: {item.question}**")
            st.session_state.quiz_answers[idx] = st.radio(
                f"Q{idx+1}", options=item.options, key=f"q_{idx}", label_visibility="collapsed"
            )
            
        if st.button("Submit Answers"): st.session_state.quiz_submitted = True
            
        if st.session_state.quiz_submitted:
            score = 0
            for idx, item in enumerate(data.quiz):
                user = st.session_state.quiz_answers.get(idx)
                correct = item.options[item.correct_index]
                if user == correct:
                    score += 1
                    st.success(f"✔️ Q{idx+1}: Correct choice!")
                else:
                    st.error(f"❌ Q{idx+1}: Incorrect. Correct Answer: {correct}")
            st.metric("Total Score", f"{score} / {len(data.quiz)}")
            
    with tab6:
        st.header("📄 Semester Mock Sample Paper")
        for idx, q in enumerate(data.sample_paper):
            st.markdown(f"### {q.section}")
            st.markdown(f"**Question {idx+1} ({q.marks} Marks):** {q.question_text}")
            with st.expander("🔍 Reveal Evaluation Criteria & Answer Guide"):
                st.write(q.marking_scheme)
            st.markdown("---")
            
elif not api_key:
    st.warning("Please configure your Gemini API token to begin processing audio files.")
else:
    st.info("Record a live classroom discussion via microphone or upload an audio clip to start generating.")
