pip install google-genai streamlit

import streamlit as st
import os
import json
import tempfile
from google import genai
from google.genai import types

# 1. Page Configuration
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

# 2. Initialization & Security Check
# Access key safely through Streamlit secrets management
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
else:
    st.info("To run this locally without deployment, add your API key below.", icon="🔑")
    api_key = st.text_input("Enter Gemini API Key", type="password")

# Instantiate the modern Google GenAI Client
client = genai.Client(api_key=api_key) if api_key else None

# Maintain persistent state for quiz progress
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

# 3. Sidebar Uploader
with st.sidebar:
    st.header("Upload Lecture Audio")
    uploaded_file = st.file_uploader("Choose an audio file...", type=["mp3", "wav", "m4a", "ogg"])
    
    if uploaded_file:
        st.audio(uploaded_file, format=uploaded_file.type)

# 4. Processing Engine
if client and uploaded_file:
    if st.sidebar.button("✨ Generate Study Guide", type="primary"):
        with st.spinner("🧠 Gemini is listening to your lecture and mapping concepts..."):
            
            # Save Streamlit's UploadedFile to a temporary local file so the SDK can ingest it
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as temp_file:
                temp_file.write(uploaded_file.read())
                temp_file_path = temp_file.name
            
            try:
                # Use File API for uploading large media content chunks
                audio_media = client.files.upload(file=temp_file_path)
                
                # Prompt enforcing Structured JSON Output mapping to avoid execution breakages
                prompt = (
                    "Analyze this audio lecture thoroughly. Generate a structured response containing: "
                    "1. A comprehensive text summary broken into major themes. "
                    "2. A set of 4 conceptual flashcards (each with a front question and back answer). "
                    "3. A 3-question multiple-choice quiz based on the key definitions discussed. "
                    "Return the response strictly adhering to JSON format matching this schema:\n"
                    "{\n"
                    "  'summary': 'string markdown format summary',\n"
                    "  'flashcards': [{'front': 'string', 'back': 'string'}],\n"
                    "  'quiz': [{'question': 'string', 'options': ['string'], 'correct_index': 0}]\n"
                    "}"
                )
                
                # Invoke Gemini 2.5 Flash for rapid audio understanding multimodal loops
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[prompt, audio_media],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.2
                    )
                )
                
                # Cleanup the cloud uploaded file reference after processing
                client.files.delete(name=audio_media.name)
                
                # Save structured elements out to persistent runtime memory context
                st.session_state.study_data = json.loads(response.text)
                st.session_state.quiz_submitted = False
                st.session_state.quiz_answers = {}
                st.success("Study materials generated successfully!")
                
            except Exception as e:
                st.error(f"Processing failed: {e}")
            finally:
                # Clean up local system OS temp directory paths 
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)

# 5. Dynamic Dashboard UI
if "study_data" in st.session_state:
    data = st.session_state.study_data
    
    tab1, tab2, tab3 = st.tabs(["📝 Interactive Summary", "🗂️ Concept Flashcards", "🧠 Knowledge Quiz"])
    
    with tab1:
        st.header("Lecture Summary Breakdowns")
        st.markdown(data.get("summary", "No summary generated."))
        
    with tab2:
        st.header("Hover Cards to Flip")
        flashcards = data.get("flashcards", [])
        
        # Grid layout deployment for cards
        cols = st.columns(2)
        for idx, card in enumerate(flashcards):
            col = cols[idx % 2]
            with col:
                card_html = f"""
                <div class="flip-card">
                    <div class="flip-card-inner">
                        <div class="flip-card-front">
                            <strong>{card.get('front')}</strong>
                        </div>
                        <div class="flip-card-back">
                            <span>{card.get('back')}</span>
                        </div>
                    </div>
                </div>
                """
                st.markdown(card_html, unsafe_allow_html=True)
                
    with tab3:
        st.header("Test Your Understanding")
        quiz = data.get("quiz", [])
        
        for idx, item in enumerate(quiz):
            st.markdown(f"**Q{idx+1}: {item.get('question')}**")
            
            # Persist selection states across interactive context reruns
            current_choice = st.radio(
                f"Select an option for question {idx+1}:", 
                options=item.get("options", []), 
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
            
            for idx, item in enumerate(quiz):
                user_ans = st.session_state.quiz_answers.get(idx)
                correct_idx = item.get("correct_index", 0)
                correct_ans = item.get("options")[correct_idx]
                
                if user_ans == correct_ans:
                    score += 1
                    st.success(f"✔️ **Question {idx+1}: Correct!** You chose: {user_ans}")
                else:
                    st.error(f"❌ **Question {idx+1}: Incorrect.** You chose: {user_ans} | **Correct Answer:** {correct_ans}")
                    
            st.metric(label="Final Score", value=f"{score} / {len(quiz)}")

elif not api_key:
    st.warning("Please configure your Gemini API token to begin processing audio files.")
else:
    st.info("Upload an audio file on the left sidebar and click 'Generate Study Guide' to begin!")
