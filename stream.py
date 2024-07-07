import streamlit as st
from main import transcribe_and_analyze, history, save_history, load_history, create_pdf, revise_answer
from template import questions

def authenticate(username, password):
    return username == "user" and password == "pass"

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if authenticate(username, password):
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

else:
    st.sidebar.title("Navigation")
    st.sidebar.write("User: User")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.experimental_rerun()

    st.sidebar.title("History")
    history_data = load_history()
    if history_data:
        for idx, session in enumerate(history_data):
            with st.sidebar.expander(f"Session {idx + 1}"):
                st.write(f"Audio File: {session['audio_file']}")
                st.write(f"Transcript Text: {session['transcript_text']}")
                st.write(f"Company File: {session['company_file']}")
                st.write(f"Company Info Source: {session['company_info_source']}")
                st.write(f"Final Questions and Answers: {session['final_questions_and_answers']}")
    else:
        st.sidebar.write("No history available.")

    st.title("Meeting Analysis Tool")
    
    st.header("Upload Files")
    audio_file = st.file_uploader("Upload Meeting Recording", type=["mp3", "wav", "mp4"])
    company_info = st.file_uploader("Upload Company Information", type=["pdf", "docx", "ppt", "txt"])
    company_info_link = st.text_input("provide a website link for company information")

    st.header("Select Template")
    templates = list(questions.keys())
    selected_template = st.selectbox("Select a Template", templates)
    if st.button("Proceed"):
        # if selected_template and audio_file and (company_info or company_info_link):
        st.session_state.questions = questions[selected_template]
        st.session_state.answers = transcribe_and_analyze(audio_file, company_info, company_info_link, st.session_state.questions)
        st.success("Files uploaded successfully and template selected")
        # else:
            # st.error("Please select a template, upload an audio file, and provide company information")

    if 'questions' in st.session_state and 'answers' in st.session_state:
        st.header("Edit Answers")
        answers = []
        instructions = []
        for i, qa in enumerate(st.session_state.answers):
            st.write(f"**{qa['question']}**")
            answer = st.text_area(f"Answer {i+1}", value=qa['answer'], key=f"answer_{i+1}")
            answers.append(answer)
            
            instruction = st.text_input(f"Instruction for Answer {i+1}", key=f"instruction_{i+1}")
            instructions.append(instruction)
            
            if st.button(f"Revise Answer {i+1}", key=f"revise_{i+1}"):
                revised_answer = revise_answer(answer, instruction)
                st.session_state.answers[i]['answer'] = revised_answer
                st.experimental_rerun()
        
        if st.button("Save"):
            st.session_state.final_answers = [{"question": st.session_state.questions[i], "answer": ans} for i, ans in enumerate(answers)]
            save_history({
                "audio_file": history["audio_file"],
                "transcript_text": history["transcript_text"],
                "company_file": history["company_file"],
                "company_info_source": history["company_info_source"],
                "final_questions_and_answers": st.session_state.final_answers
            })
            st.success("Answers saved successfully")

    if 'final_answers' in st.session_state:
        st.header("Download Final Document")
        if st.button("Generate Document"):
            pdf_doc = create_pdf(st.session_state.final_answers, "final_answers.pdf")
            st.download_button(label="Download PDF", data=pdf_doc, file_name="final_answers.pdf", mime="application/pdf")
