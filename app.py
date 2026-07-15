import streamlit as st
import os
import tempfile
import base64
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List
from gtts import gTTS

# 1. Define Strict Pydantic Schemas for Multi-Feature Outputs
class Flashcard(BaseModel):
    front: str = Field(description="The conceptual question or definition term.")
    back: str = Field(description="The answer or detailed explanation.")

class QuizItem(BaseModel):
    question: str = Field(description="The multiple choice question text.")
    options: List[str] = Field(description="Exactly 4 realistic option choices.")
    correct_index: int = Field(description="The index (0-3) of the correct option.")

class VideoFrame(BaseModel):
    scene_description: str = Field(description="Detailed visual prompt describing what should be shown on screen.")
    voiceover_script: str = Field(description="The word-for-word voiceover script explaining this specific sub-concept.")

class SamplePaperQuestion(BaseModel):
    section: str = Field(description="Section name (e.g., Section A: Short Answer, Section B: Long Essay)")
    marks: int = Field(description="Weight of the question (e.g., 5, 10)")
    question_text: str = Field(description="The academic exam question.")
    marking_scheme: str = Field(description="Detailed grading points required for full marks.")

class StudyGuideSchema(BaseModel):
    summary: str = Field(description="A comprehensive markdown summary of the major lecture themes.")
    mindmap_mermaid: str = Field(description="A valid, well-structured Mermaid.js syntax flowchart using graph TD. Do not wrap in markdown quotes inside the JSON string.")
    flashcards: List[Flashcard] = Field(description="A list of 4 concept flashcards.")
    quiz: List[QuizItem] = Field(description="A list of 3 diagnostic multiple-choice questions.")
    video_storyboard: List[VideoFrame] = Field(description="Exactly 3 sequential concept frames that explain the core topic visually and auditorily.")
    sample_paper: List[SamplePaperQuestion] = Field(description="A full comprehensive 4-question mock exam paper covering the material.")

# 2. Page Configuration & Custom CSS Injection
st.set_page_config(page_title="Neuro-Notes Studio", page_icon="🧠", layout="wide")

st.markdown("""
<style>
    .flip-card { background-color: transparent; width: 100%; height: 180px; perspective: 1000px; margin-bottom: 20px; }
    .flip-card-inner { position: relative; width: 100%; height: 100%; text-align: center; transition: transform 0.6s; transform-style: preserve-3d; cursor: pointer; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); border-radius: 10px; }
    .flip-card:hover .flip-card-inner { transform: rotateY(180deg); }
    .flip-card-front, .flip-card-back { position: absolute; width: 100%; height: 100%; -webkit-backface-visibility: hidden; backface-visibility: hidden; display: flex; align-items: center; justify-content: center; padding: 20px; border-radius: 10px; }
    .flip-card-front { background-color: #262730; color: white; border: 1px solid #464855; }
    .flip-card-back { background-color: #FF4B4B; color: white; transform: rotateY(180deg); }
    .scene-box { background-color: #1E1E24; border-left: 5px solid #00E676; padding: 20px; margin-bottom: 15px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Neuro-Notes AI Classroom Studio")
st.caption("Live record or upload your classes to create summaries, code-rendered mind maps, animation sequences, and test papers.")

# 3. Security Check
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.info("Add your API key below if running outside deployment environments.", icon="🔑")
    api_key = st.text_input("Enter Gemini API Key", type="password")

client = genai.Client(api_key=api_key) if api_key else None

# State Inits
if "quiz_answers" not in st.session_state: st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state: st.session_state.quiz_submitted = False

# 4. Multi-Input Panel (Sidebar)
with st.sidebar:
    st.header("🎙️ Classroom Audio Source")
    input_method = st.radio("Choose Input Method:", ["🔴 Live Record Class", "📁 Upload Audio File"])
    
    audio_data = None
    if input_method == "🔴 Live Record Class":
        # Native web microphone capture component
        audio_data = st.audio_input("Tap Microphone to Record Live Class Lecture")
    else:
        audio_data = st.file_uploader("Upload Lecture File", type=["mp3", "wav", "m4a", "ogg"])
        if audio_data:
            st.audio(audio_data, format=audio_data.type)

# 5. Multimodal Ingestion Engine
if client and audio_data:
    if st.sidebar.button("✨ Compile Complete Lecture Assets", type="primary"):
        with st.spinner("🧠 Synthesizing structures, video boards, and question configurations..."):
            
            # Write bytes stream to disk securely
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data.read() if hasattr(audio_data, 'read') else audio_data.getvalue())
                temp_file_path = temp_file.name
            
            try:
                audio_media = client.files.upload(file=temp_file_path)
                
                prompt = (
                    "Thoroughly analyze this classroom lecture recording. Extract all foundational structural metadata "
                    "and construct the requested schema. Generate high-quality values, translate insights "
                    "into educational flashcards, design detailed text-to-speech video scenes, draft rigorous sample papers, "
                    "and generate complete valid Mermaid flowchart logic modeling the core concepts."
                )
                
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=[prompt, audio_media],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=StudyGuideSchema,
                        temperature=0.3
                    )
                )
                
                client.files.delete(name=audio_media.name)
                st.session_state.study_data = response.parsed
                st.session_state.quiz_submitted = False
                st.session_state.quiz_answers = {}
                st.success("All dynamic assets generated successfully!")
                
            except Exception as e:
                st.error(f"Processing error: {e}")
            finally:
                if os.path.exists(temp_file_path): os.remove(temp_file_path)

# 6. Advanced Tab Dashboard
if "study_data" in st.session_state:
    data = st.session_state.study_data
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📝 Summary", "🌿 Interactive Mind-Map", "🎬 Video Presentation", "🗂️ Flashcards", "🧠 Quiz", "📄 Mock Exam Paper"
    ])
    
    with tab1:
        st.header("Lecture Breakdown Summary")
        st.markdown(data.summary)
        
    with tab2:
        st.header("Visual Lecture Mind-Map Graph")
        st.caption("Auto-generated interactive conceptual roadmap.")
        # Render clean Mermaid structures natively in markdown
        st.markdown(f"```mermaid\n{data.mindmap_mermaid}\n```")
        
    with tab3:
        st.header("AI Concept Explainer Reel")
        st.caption("Visual animation guideboards paired with instant synthesized vocal narration loops.")
        
        for idx, frame in enumerate(data.video_storyboard):
            with st.container():
                st.markdown(f"### 🎬 Scene {idx+1}")
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.markdown("**🎨 Graphic Visual Design Prompt:**")
                    st.info(frame.scene_description)
                
                with col2:
                    st.markdown("**🎙️ Audio Explainer Script:**")
                    st.code(frame.voiceover_script, language="text")
                    
                    # Synthesize real-time audio voiceover using Google TTS engine
                    try:
                        tts = gTTS(text=frame.voiceover_script, lang='en', slow=False)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tts_file:
                            tts.save(tts_file.name)
                            st.audio(tts_file.name, format="audio/mp3")
                        os.remove(tts_file.name)
                    except Exception as tts_err:
                        st.caption("Audio rendering temporarily unavailable.")
                st.markdown("---")
                
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
        st.caption("Test your full theoretical understanding with this simulated exam sheet.")
        
        paper_markdown = ""
        for idx, q in enumerate(data.sample_paper):
            paper_markdown += f"### {q.section}\n"
            paper_markdown += f"**Question {idx+1} ({q.marks} Marks):**\n"
            paper_markdown += f"> {q.question_text}\n\n"
            
            with st.expander(f"🔍 Reveal Academic Marking Scheme & Ideal Answers (Q{idx+1})"):
                st.markdown("**Required Core Points for Full Score Evaluation:**")
                st.write(q.marking_scheme)
            st.markdown("---")

elif not api_key:
    st.warning("Please configure your Gemini API token to begin processing audio files.")
else:
    st.info("Record a live classroom discussion via microphone or upload an audio clip to start generating.")
