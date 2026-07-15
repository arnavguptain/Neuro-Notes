import streamlit as st
import os
import tempfile
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

# 1. Define Native Pydantic Schemas for Strict Constraint Output
class Flashcard(BaseModel):
    front: str = Field(description="The conceptual question or definition term.")
    back: str = Field(description="The answer or detailed explanation.")

class QuizItem(BaseModel):
    question: str = Field(description="The multiple choice question text based on the audio lecture.")
    options: List[str] = Field(description="Exactly 4 realistic option choices for the user.")
    correct_index: int = Field(description="The index (0-3) of the correct option inside the options array.")

class StudyGuideSchema(BaseModel):
    summary: str = Field(description="A comprehensive, detailed markdown summary of the major themes in the audio.")
    flashcards: List[Flashcard] = Field(description="A list of 4 high-quality concept flashcards.")
    quiz: List[QuizItem] = Field(description="A list of 3 relevant diagnostic multiple-choice questions.")

# 2. Page Configuration
st.set_page_config(page_title="Neuro-Notes: AI Study Guide", page_icon="🧠", layout="wide")

# Custom CSS for the 3D Flipping Flashcards
st.markdown("""
<style>
    .flip-card {
        background-color: transparent;
        width: 100%;
        height: 200px;
        perspective: 1000px;
        margin-bottom: 20px;
    }
    .flip-card-inner {
        position: relative;
        width: 100%;
        height: 100%;
        text-align: center;
        transition: transform 0.6s;
        transform-style: preserve-3d;
        cursor: pointer;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2);
        border-radius: 10px;
    }
    .flip-card:hover .flip-card-inner {
        transform: rotateY(180deg);
    }
    .flip-card-front, .flip-card-back {
        position: absolute;
        width: 100%;
        height: 100%;
        -webkit-backface-visibility: hidden;
        backface-visibility: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
        border-radius: 10px;
    }
    .flip-card-front {
        background-color: #262730;
        color: white;
        border: 1px solid #464855;
    }
    .flip-card-back {
        background-color: #FF4B4B;
        color: white;
        transform: rotateY(180deg);
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 Neuro-Notes")
st.caption("Transform audio lectures and voice memos into visual interactive study guides.")

# 3. Initialization & Security Check
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.info("To run this locally without deployment, add your API key below.", icon="🔑")
    api_key = st.text_input("Enter Gemini API Key", type="password")

client = genai.Client(api_key=api_key) if api_key else None

if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

# 4. Sidebar Uploader
with st.sidebar:
    st.header("Upload Lecture Audio")
    uploaded_file = st.file_uploader("Choose an audio file...", type=["mp3", "wav", "m4a", "ogg"])
    
    if uploaded_file:
        st.audio(uploaded_file, format=uploaded_file.type)

# 5. Processing Engine
if client and uploaded_file:
    if st.sidebar.button("✨ Generate Study Guide", type="primary"):
        with st.spinner("🧠 Gemini is listening to your lecture and mapping concepts..."):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
                temp_file.write(uploaded_file.read())
                temp_file_path = temp_file.name
            
            try:
                # Use File API for safe uploading of multimedia contents
                audio_media = client.files.upload(file=temp_file_path)
                
                # Base prompt telling the model what to extract from the source audio asset
                prompt = "Thoroughly process this lecture audio and organize it into the requested schema structure."
                
                # Using the modern SDK response_schema configurations
                response = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=[prompt, audio_media],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=StudyGuideSchema, # ⚡ Crucial: Forces native schema validation
                        temperature=0.2
                    )
                )
                
                # Cleanup the cloud asset context instance post-generation
                client.files.delete(name=audio_media.name)
                
                # The modern SDK automatically parses verified fields out into response.parsed
                st.session_state.study_data = response.parsed
                st.session_state.quiz_submitted = False
                st.session_state.quiz_answers = {}
                st.success("Study materials generated successfully!")
                
            except Exception as e:
                st.error(f"Processing failed: {e}")
            finally:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

# 6. Dynamic Dashboard UI
if "study_data" in st.session_state:
    data = st.session_state.study_data
    
    tab1, tab2, tab3 = st.tabs(["📝 Interactive Summary", "🗂️ Concept Flashcards", "🧠 Knowledge Quiz"])
    
    with tab1:
        st.header("Lecture Summary Breakdowns")
        # Direct dot notation instead of dict dictionary lookups due to parsing as a Pydantic object
        st.markdown(data.summary)
        
    with tab2:
        st.header("Hover Cards to Flip")
        
        cols = st.columns(2)
        for idx, card in enumerate(data.flashcards):
            col = cols[idx % 2]
            with col:
                card_html = f"""
                <div class="flip-card">
                    <div class="flip-card-inner">
                        <div class="flip-card-front">
                            <strong>{card.front}</strong>
                        </div>
                        <div class="flip-card-back">
                            <span>{card.back}</span>
                        </div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
    with tab3:
        st.header("Test Your Understanding")
        
        for idx, item in enumerate(data.quiz):
            st.markdown(f"**Q{idx+1}: {item.question}**")
            
            current_choice = st.radio(
                f"Select an option for question {idx+1}:", 
                options=item.options, 
                key=f"q_radio_{idx}",
                label_visibility="collapsed"
            )
            st.session_state.quiz_answers[idx] = current_choice
            st.write("")
            
        if st.button("Submit Answers", type="secondary"):
            st.session_state.quiz_submitted = True
            
        if st.session_state.quiz_submitted:
            score = 0
            st.markdown("---")
            st.subheader("Results:")
            
            for idx, item in enumerate(data.quiz):
                user_ans = st.session_state.quiz_answers.get(idx)
                correct_ans = item.options[item.correct_index]
                
                if user_ans == correct_ans:
                    score += 1
                    st.success(f"✔️ **Question {idx+1}: Correct!** You chose: {user_ans}")
                else:
                    st.error(f"❌ **Question {idx+1}: Incorrect.** You chose: {user_ans} | **Correct Answer:** {correct_ans}")
                    
            st.metric(label="Final Score", value=f"{score} / {len(data.quiz)}")

elif not api_key:
    st.warning("Please configure your Gemini API token to begin processing audio files.")
else:
    st.info("Upload an audio file on the left sidebar and click 'Generate Study Guide' to begin!")
