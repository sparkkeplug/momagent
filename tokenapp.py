import streamlit as st
# Use faster-whisper instead of openai-whisper
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    st.error("⚠️ Whisper is not installed. Please run: pip install faster-whisper")

import tempfile
import os
import base64
import requests, uuid
from dotenv import load_dotenv
load_dotenv()

def save_mom_to_txt(mom_output, output_path="mom_output.txt"):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(mom_output)
    print(f"Text file saved to: {output_path}")
    return output_path

# Model call
def call_ollama_model(prompt: str) -> str:
    """Query Hugging Face Inference API using your access token"""
    headers = {
        "Authorization": f"Bearer {os.getenv('HF_TOKEN')}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": os.getenv("MODEL_NAME"),
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    try:
        response = requests.post(os.getenv("API_URL"), headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"❌ Exception: {str(e)}"

# --- Streamlit App ---
st.set_page_config(page_title="MOM Generator", layout="wide")
st.markdown("""
    <h1 style='text-align: center; color: #ffffff; font-size: 3em; font-weight: bold; margin-bottom: 0.5em;'>
        🎙️ Minutes of Meeting Generator 🎙️
    </h1>
""", unsafe_allow_html=True)

# Choose input type
if WHISPER_AVAILABLE:
    input_option = st.radio("Choose your input type:", ["📁 Upload Audio (.mp3)", "📝 Upload Transcript (.txt or .docx)"])
else:
    input_option = st.radio("Choose your input type:", ["📝 Upload Transcript (.txt or .docx)"])
    st.warning("⚠️ Audio transcription is not available. Please install faster-whisper: `pip install faster-whisper`")

transcript = ""

# Handle audio input
if input_option == "📁 Upload Audio (.mp3)" and WHISPER_AVAILABLE:
    audio_file = st.file_uploader("Upload meeting audio (.mp3)", type=["mp3"])
    if audio_file is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(audio_file.read())
            tmp_path = tmp.name
        st.audio(audio_file, format='audio/mp3')
        st.write("🔄 Transcribing audio using Whisper...")
        
        try:
            # Use faster-whisper instead
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(tmp_path, beam_size=5)
            transcript = " ".join([segment.text for segment in segments])
        except Exception as e:
            st.error(f"Error during transcription: {str(e)}")
            transcript = ""
        finally:
            os.remove(tmp_path)

# Handle transcript input
elif input_option == "📝 Upload Transcript (.txt or .docx)":
    txt_file = st.file_uploader("Upload transcript (.txt or .docx)", type=["txt", "docx"])
    if txt_file is not None:
        if txt_file.name.endswith(".txt"):
            transcript = txt_file.read().decode("utf-8")
        elif txt_file.name.endswith(".docx"):
            doc = Document(txt_file)
            transcript = "\n".join([para.text for para in doc.paragraphs])

# Process if transcript is ready
if transcript:
    st.subheader("📝 Transcript Generated:")
    st.download_button("⬇️ Download Transcript as .txt", transcript, file_name="transcript.txt")

    st.write("🤖 Generating Minutes of Meeting (MOM)...")
    
    MOM_PROMPT = f"""
Please analyze the following meeting transcript and generate a comprehensive "Minutes of Meeting" (MOM) document.

The MOM should be structured with the following sections. If any information is not explicitly available in the transcript, please indicate "N/A" or "Not specified" for that field.

**Meeting Transcript:** {transcript}

---  
**MOM Structure:**  
# Minutes of Meeting  
## 1. Meeting Information  
***Date:*** [Extract Date, e.g., YYYY-MM-DD]  
***Time:*** [Extract Start and End Time, e.g., HH:MM AM/PM - HH:MM AM/PM]  
***Location:*** [Extract Location, if specified, e.g., Conference Room A, Virtual Call]  
***Meeting Title/Subject:*** [Extract main topic or title of the meeting]  

## 2. Attendees  
***Chairperson:*** [Name of the person leading the meeting, if specified]  
***Scribe/Minute Taker:*** [Name of the person taking minutes, if specified]  
***Present:***  
* [List all attendees present, preferably with their roles/affiliations if available]  
***Absent (with apologies):***  
* [List attendees who were expected but absent, if mentioned]  

## 3. Agenda  
* [List each agenda item discussed]  

## 4. Key Discussions & Decisions  
* **Topic 1:**  
  * Discussion point 1  
  * Decision/Outcome  
* **Topic 2:**  
  * ...  

## 5. Action Items  
* `[Action Item] - [Responsible Person(s)] - [Due Date]`  

## 6. Next Meeting  
***Date:***  
***Time:***  
***Location:***  
***Key Topics for Next Meeting:***
"""

    with st.spinner("Generating MOM using model...."):
        mom_output = call_ollama_model(MOM_PROMPT)

    txt_path = save_mom_to_txt(mom_output)
    with open(txt_path, "rb") as f:
        base64_txt = base64.b64encode(f.read()).decode("utf-8")
        txt_link = f'<a href="data:application/octet-stream;base64,{base64_txt}" download="Minutes_of_Meeting.txt">📄 Download MOM as Txt</a>'
        st.markdown(txt_link, unsafe_allow_html=True)

    html_output_path = os.path.join(tempfile.gettempdir(), "MOM_Output.html")
    with open(html_output_path, "w", encoding="utf-8") as html_file:
        html_file.write(f"<html><body><pre>{mom_output}</pre></body></html>")

    with open(html_output_path, "r", encoding="utf-8") as f:
        html_download = f.read()
        b64 = base64.b64encode(html_download.encode()).decode()
        st.markdown(
            f'<a href="data:text/html;base64,{b64}" download="Minutes_of_Meeting.html">🌐 Download MOM as HTML</a>',
            unsafe_allow_html=True
        )

    st.subheader("📋 Minutes of Meeting 📋")
   
    st.markdown(f"""
        <div style='
        background: repeating-linear-gradient(white, white 24px, #d2e0fc 25px, white 26px);
        line-height: 20px;
        font-family: Courier New, monospace;
        padding: 20px;
        border: 2px solid #4682B4;
        border-radius: 10px;
        white-space: normal;
        overflow-x: auto;
        overflow-y: auto;
        color: black;
        '>
        {mom_output}
        </div>
        """, unsafe_allow_html=True)
    
    # ✅ Sidebar Chat with MOM Assistant
    st.markdown("## 💬 Chat with MOM Assistant")

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'input_key' not in st.session_state:
        st.session_state.input_key = str(uuid.uuid4())

    user_input = st.text_area("Your instruction...", key=st.session_state.input_key)
    send_button = st.button("Send")

    if send_button and user_input.strip():
        prev_mom = st.session_state.get('mom_output', mom_output)
        full_prompt = f"""This is the transcript: {transcript}
                        This is the current version of the MOM:

                        {prev_mom}

                        Now please follow this instruction:
                        {user_input}
                        """
        st.session_state.chat_history.append(("You", user_input))
        with st.spinner("MOM Assistant is processing..."):
            response = call_ollama_model(full_prompt)
        st.session_state.chat_history.append(("MOM Assistant", response))
        st.session_state.mom_output = response
        st.session_state.input_key = str(uuid.uuid4())

    # Show chat history
    for sender, message in st.session_state.chat_history:            
        if sender == "MOM Assistant":
            st.markdown(f"**{sender}:**" + f"""<div style='background: repeating-linear-gradient(white, white 24px, #d2e0fc 25px, white 26px);line-height: 20px;font-family: Courier New, monospace;padding: 20px;border: 2px solid #4682B4;border-radius: 10px;
                                                        white-space: normal;
                                                        overflow-x: auto;
                                                        overflow-y: auto;
                                                        color: black;
                    '>
    {message}</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"**{sender}:** {message}")
