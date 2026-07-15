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

# 1. Schema Layout Constraints matching CBSE Matrix Blueprints
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

class CBSESamplePaperQuestion(BaseModel):
    section: str = Field(description="CBSE Section allocation string (e.g., Section A [Objective], Section B [Competency Based], Section C [Subjective Short/Long Answer])")
    marks: int = Field(description="Weight of the question matching standard split metrics (e.g., 1, 3, or 5 marks).")
    question_text: str = Field(description="The academic exam question tailored around application mechanics.")
    marking_scheme: str = Field(description="Granular assessment criteria blueprint points detailing full credit paths.")

class StudyGuideSchema(BaseModel):
    detailed_notes: str = Field(description="In-depth, textbook-quality academic notes. Use standard markdown structure with clean headers (##), bold terms, lists, and proper paragraphs.")
    mindmap_mermaid: str = Field(description="A valid, well-structured Mermaid.js syntax flowchart using graph TD.")
    flashcards: List[Flashcard] = Field(description="A list of 4 concept flashcards.")
    quiz: List[QuizItem] = Field(description="A list of 3 diagnostic multiple-choice questions.")
    video_storyboard: List[VideoFrame] = Field(description="Exactly 4 sequential animation frames to build a continuous explainer video.")
    sample_paper: List[CBSESamplePaperQuestion] = Field(description="A full comprehensive 4-question mock exam paper mapped rigidly against standard CBSE weight criteria matrices.")

# 2. Page Configuration & Custom Premium Dark Theme Styling
st.set_page_config(page_title="Neuro-Notes Studio Pro", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .main-title { font-size: 2.8rem; font-weight: 800; color: #FF4B4B; margin-bottom: 5px; }
    .subtitle { color: #A3A8B4; font-size: 1.05rem; margin-bottom: 25px; }
    
    /* Premium CBSE Alert Board */
    .cbse-alert { background-color: #1A1C24; border-left: 5px solid #FF9F43; padding: 15px; border-radius: 4px; margin-bottom: 20px; color: #E2E8F0; }
    
    /* 3D Interactive Flashcards */
    .flip-card { background-color: transparent; width: 100%; height: 180px; perspective: 1000px; margin-bottom: 25px; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; cursor: pointer; box-shadow: 0 8px 16px rgba(0,0,0,0.3); border-radius: 12px; }
    .flip-card:hover .flip-card-inner { transform: rotateY(180deg); }
    .flip-card-front, .flip-card-back { position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 20px; border-radius: 12px; }
    .flip-card-front { background-color: #1E2028; color: #FFFFFF; border: 1px solid #3A3F50; }
    .flip-card-back { background-color: #FF4B4B; color: white; transform: rotateY(180deg); }
    
    .evaluation-box { background-color: #111318; border: 1px dashed #4E546C; padding: 20px; border-radius: 8px; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🧠 Neuro-Notes Studio Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Convert educational audio streams into clean interactive video reels, custom conceptual mind maps, and CBSE-compliant structural testing suites.</div>', unsafe_allow_html=True)

# 3. Security Check
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    api_key = st.text_input("Enter Gemini API Key", type="password")

client = genai.Client(api_key=api_key) if api_key else None

if "quiz_answers" not in st.session_state: st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state: st.session_state.quiz_submitted = False

# 4. Input Configuration Channel Selector Sidebar
with st.sidebar:
    st.header("🎙️ Lecture Input Channel")
    input_method = st.radio("Choose Input Method:", ["🔴 Live Record Class", "📁 Upload Audio File"])
    audio_data = st.audio_input("Microphone") if input_method == "🔴 Live Record Class" else st.file_uploader("Upload Audio Resource File", type=["mp3", "wav", "m4a", "ogg"])

# Helper function to generate clean standard animation matrices
def render_animation_video(storyboard):
    width, height = 960, 540
    fps = 10
    temp_avi = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    video_writer = cv2.VideoWriter(temp_avi.name, fourcc, fps, (width, height))
    if not video_writer.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(temp_avi.name, fourcc, fps, (width, height))

    for frame_idx, frame in enumerate(storyboard):
        img = Image.new("RGB", (width, height), color=(22, 24, 30))
        draw = ImageDraw.Draw(img)
        
        draw.rectangle([(25, 25), (935, 515)], outline=(46, 50, 62), width=3)
        draw.rectangle([(35, 35), (925, 85)], fill=(34, 38, 48))
        draw.text((50, 48), f"LESSON CHAPTER TOPIC: {frame.slide_title.upper()}", fill=(255, 75, 75))
        
        y_offset = 160
        for pt in frame.slide_text_points:
            draw.text((70, y_offset), f"• {pt}", fill=(230, 235, 245))
            y_offset += 75
            
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        for _ in range(fps * 6):
            video_writer.write(cv_img)
            
    video_writer.release()
    return temp_avi.name

# 5. Core Operational Flow Orchestration Engine
if client and audio_data:
    if st.sidebar.button("✨ Compile Complete Lecture Assets", type="primary"):
        with st.spinner("🧠 Synthesizing premium textbook notes, hierarchy roadmaps, and running explainer animations..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data.read() if hasattr(audio_data, 'read') else audio_data.getvalue())
                temp_file_path = temp_file.name
            
            try:
                audio_media = client.files.upload(file=temp_file_path)
                
                prompt = (
                    "Process this classroom lecture recording completely. Generate comprehensive, cleanly formatted, "
                    "textbook-quality academic notes inside the detailed_notes schema parameter, ensuring clean markdown structure. "
                    "Create complete Mermaid roadmap trees, concept flashcards, diagnostic evaluation questions, and exact presentation slide frames. "
                    "Crucially, format the sample_paper array items to perfectly model standard CBSE exam structural specifications (40% MCQs, 20% competency questions, 40% long/short subjective answers split framework)."
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
                if "grading_result" in st.session_state: del st.session_state.grading_result
                
                raw_video_output_path = render_animation_video(response.parsed.video_storyboard)
                with open(raw_video_output_path, "rb") as f:
                    st.session_state.video_base64 = base64.b64encode(f.read()).decode("utf-8")
                os.remove(raw_video_output_path)
                
                st.success("All dynamic study framework structures successfully built!")
                
            except Exception as e:
                st.error(f"Processing error encountered: {e}")
            finally:
                if os.path.exists(temp_file_path): os.remove(temp_file_path)

# 6. Interactive Multi-Tab Study Dashboard Interface
if "study_data" in st.session_state:
    data = st.session_state.study_data
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🎬 Concept Explainer Animation", "📝 Detailed Textbook Notes", "🌿 Hierarchical Mind-Map", "🗂️ Flashcards Module", "🧠 Diagnostic Quiz", "📄 CBSE Assessment & Photo Grading"
    ])
    
    with tab1:
        st.subheader("🎬 Dynamic Lecture Concepts Short Animation Video")
        if "video_base64" in st.session_state:
            st.markdown(f"""
            <div style="max-width: 960px; margin: 0 auto;">
                <video width="100%" height="auto" controls autoplay muted style="border-radius:12px; border:2px solid #2e323e; box-shadow: 0 12px 24px rgba(0,0,0,0.5);">
                    <source src="data:video/mp4;base64,{st.session_state.video_base64}" type="video/mp4">
                    Your browser does not support playing this animation file.
                </video>
            </div>
            """, unsafe_allow_html=True)
        
    with tab2:
        st.subheader("📚 Rigorous Lecture Study Notes")
        st.markdown(data.detailed_notes.replace(r'\n', '\n'))
        
    with tab3:
        st.subheader("🌿 Conceptual Roadmap Trees")
        st.markdown(f"```mermaid\n{data.mindmap_mermaid}\n```")
        
    with tab4:
        st.subheader("🗂️ 3D Concept Cards Revision Space")
        cols = st.columns(2)
        for idx, card in enumerate(data.flashcards):
            with cols[idx % 2]:
                st.markdown(f"""
                <div class="flip-card">
                    <div class="flip-card-inner">
                        <div class="flip-card-front">
                            <span style="color:#FF4B4B; font-weight:bold; margin-bottom:8px;">TERM CONCEPT</span>
                            <strong>{card.front}</strong>
                        </div>
                        <div class="flip-card-back">
                            <span style="font-weight:bold; margin-bottom:8px;">ANSWER KEY DETAILED MATRIX</span>
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
        st.subheader("📄 CBSE Formatted Reference Framework Mock Examination Paper")
        
        # Rigorous CBSE Statutory Rules Display Notice Board
        st.markdown("""
        <div class="cbse-alert">
            <strong>⚠️ NATIVE CBSE EXAMINATION STRATEGY INSTRUCTIONS & COMPLIANCE REQUIREMENTS:</strong><br>
            • <strong>Cool-off Period:</strong> Students are strictly required to use the initial 15-minute cool-off period exclusively for reading through question sections.<br>
            • <strong>Sectional Layout Separation:</strong> Question structures map out exactly to 40% Objective MCQs, 20% Competency Case-Studies, and 40% Subjective criteria frameworks. You must solve dedicated section points inside unified blocks.<br>
            • <strong>Margin & Paper Geometry Control:</strong> Question structural indices must be written <strong>ONLY in the left-hand margin space</strong>. Use the right-side margins exclusively for scratch space and strike it out with a clean diagonal row line upon end.<br>
            • <strong>Correction & Pen Control rules:</strong> No whiteners or messy cross-out patterns allowed. Draw a single horizontal tracking line across errors. Write exclusively with blue/black ink tools. All stationery items must sit inside a completely transparent containment pouch.
        </div>
        """, unsafe_allow_html=True)
        
        for idx, q in enumerate(data.sample_paper):
            st.info(f"👉 **{q.section} — [ALLOCATED WEIGHT: {q.marks} MARKS]**")
            st.markdown(f"**Question {idx+1}:** {q.question_text}")
            with st.expander("🔍 Show CBSE Answer Blueprint Evaluation Keys"):
                st.write(q.marking_scheme)
            st.markdown("---")
            
        # AI Custom Notebook Visual Evaluation Desk Engine Area
        st.subheader("📷 Notebook Handwriting Grading Hub")
        st.caption("Write the answers inside your physical homework paper booklet using standard CBSE margin tracking formats, click a clear picture via camera capture, and evaluate instantly.")
        
        captured_image = st.camera_input("Scan Notebook Answer Workspace Sheet Page")
        
        if captured_image:
            st.image(captured_image, caption="Uploaded Sheet Snapshot Preview")
            
            if st.button("🚀 Run AI Answer Analysis & Grade Work", type="primary"):
                with st.spinner("🤖 Evaluating handwriting strings against reference scoring frameworks..."):
                    try:
                        # Direct image processing bytes transformation pipelines
                        img_bytes = captured_image.getvalue()
                        
                        # Pack structured baseline validation matrices to safely supply the Gemini processing node
                        image_part = types.Part.from_bytes(
                            data=img_bytes,
                            mime_type="image/jpeg",
                        )
                        
                        grading_prompt = f"""
                        You are a strict CBSE Board Evaluator. Grade this student's uploaded handwritten answer sheet photo.
                        
                        Cross-reference their writing style layout against the provided sample mock paper guidelines:
                        {data.sample_paper}
                        
                        Check for compliance with standard layout rules:
                        1. Did they write question indices correctly inside the LEFT margin?
                        2. Is there clean text layout without whitener fluid use?
                        3. Is the conceptual answer logically correct based on the marking scheme?
                        
                        Provide a clean grading matrix statement breaking down marks earned per question along with short, helpful feedback strings.
                        """
                        
                        grading_response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=[grading_prompt, image_part]
                        )
                        
                        st.session_state.grading_result = grading_response.text
                        
                    except Exception as ex:
                        st.error(f"Image analytics core node processing error: {ex}")
                        
        if "grading_result" in st.session_state:
            st.markdown('<div class="evaluation-box">', unsafe_allow_html=True)
            st.markdown("### 🏆 AI Classroom Evaluation Score Sheet & Feedback")
            st.markdown(st.session_state.grading_result)
            st.markdown('</div>', unsafe_allow_html=True)

elif not api_key:
    st.warning("Please configure your Gemini API token to begin processing audio files.")
else:
    st.info("Record a live classroom discussion via microphone or upload an audio clip to start generating.")
