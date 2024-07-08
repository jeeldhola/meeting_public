import openai
import os
from typing import IO
import shutil
from fpdf import FPDF
from io import BytesIO
from template import questions
import streamlit as st
import fitz  
from docx import Document as DocxDocument
from pptx import Presentation
import requests
from bs4 import BeautifulSoup
from openai import OpenAI

api_key = "sk-taral-upwork-VqgjaTN5HZGDFmE9sIAAT3BlbkFJ8AkY3JurXEUjXh1cfnnj"

client = OpenAI(api_key=api_key)

history = {
    "audio_file": None,
    "transcript_text": None,
    "company_file": None,
    "final_questions_and_answers": None,
    "company_info_source": None
}

MAX_CONTEXT_LENGTH = 4096
MAX_FILE_SIZE = 25 * 1024 * 1024

def transcribe_audio(file_path: str) -> str:
    audio_file = open(file_path, "rb")
    transcription = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )
    transcript_text = transcription.text
    
    history["audio_file"] = os.path.basename(file_path)
    history["transcript_text"] = transcript_text
    
    return transcript_text

def upload_company_file(file: IO, filename: str) -> str:
    if not os.path.exists("company_files"):
        os.makedirs("company_files")
    file_location = os.path.join("company_files", filename)
    with open(file_location, "wb") as file_object:
        shutil.copyfileobj(file, file_object)
    history["company_file"] = filename
    history["company_info_source"] = "file"
    return f"Company info file '{filename}' uploaded successfully to '{file_location}'"

def fetch_company_info_from_link(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    company_info = soup.get_text()
    history["company_info_source"] = "link"
    return company_info


def truncate_text(text: str) -> str:


    completion = client.chat.completions.create(
      model="gpt-4o",
      messages=[
        {"role": "system", "content": "Summarize the given script and information in 1000 words."},
        {"role": "user", "content": f"{text}"}
      ]
    )

# print(c
    return completion.choices[0].message.content.strip()

def generate_answers(transcript: str, company_info: str, questions) -> list:
    combined_text = f"Based on the following transcript of a meeting and company information:\n\nTranscript:\n{transcript}\n\nCompany Information:\n{company_info}"
    truncated_text = truncate_text(combined_text)

    answers = []
    for question in questions:
        prompt = {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"{truncated_text}\n\nPlease provide a detailed and specific answer to the following question -\n\"{question}\""
                }
            ]
        }

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": "You are a helpful assistant. Given the following combined text of an audio transcript and company information, please provide a detailed and specific answer to the question provided."
                        }
                    ]
                },
                prompt
            ],
            temperature=1,
            max_tokens=3223,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        answer = response.choices[0].message.content.strip()
        answers.append({"question": question, "answer": answer})

    history["final_questions_and_answers"] = answers
    return answers

def revise_answer(original_answer, instruction):
    prompt = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": f"Original answer:\n{original_answer}\n\nInstruction:\n{instruction}\n\nPlease revise the answer according to the instruction."
            }
        ]
    }

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "You are a helpful assistant. Please revise the given answer according to the instruction provided."
                    }
                ]
            },
            prompt
        ],
        temperature=1,
        max_tokens=1500,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )

    revised_answer = response.choices[0].message.content.strip()
    return revised_answer

def create_pdf(answers: list, filename: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    
    pdf.add_font('DejaVu', '', 'font/DejaVuSans.ttf', uni=True)
    pdf.set_font('DejaVu', '', 12)
    
    for qa in answers:
        pdf.multi_cell(0, 10, txt=f"Q: {qa['question']}\nA: {qa['answer']}\n", align='L')
    
    byte_io = BytesIO()
    pdf.output(name=filename, dest='F')
    with open(filename, 'rb') as f:
        byte_io.write(f.read())
    byte_io.seek(0)
    return byte_io.getvalue()

def save_history(session_data):
    if 'history' not in st.session_state:
        st.session_state.history = []
    st.session_state.history.append(session_data)

def load_history():
    if 'history' in st.session_state:
        return st.session_state.history
    return []

def get_current_history() -> dict:
    return history

def transcribe_and_analyze(audio_file= None, company_info = None, company_info_link= None, questions):
    if audio_file and (company_info or company_info_link):
        audio_file_path = f"temp_{audio_file.name}"
        with open(audio_file_path, "wb") as f:
            f.write(audio_file.getbuffer())

        transcript_text = transcribe_audio(audio_file_path)

        if company_info:
            company_file_path = f"temp_{company_info.name}"
            with open(company_file_path, "wb") as f:
                f.write(company_info.getbuffer())
            with open(company_file_path, "r", encoding="latin-1") as f:
                company_info_text = f.read()
            history["company_file"] = company_info.name
        else:
            company_info_text = fetch_company_info_from_link(company_info_link)

        answers = generate_answers(transcript_text, company_info_text, questions)
        return answers
    return ["No audio or company file/link provided"]
