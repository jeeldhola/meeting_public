import openai
import os
from typing import IO
import shutil
from fpdf import FPDF
from io import BytesIO
from template import questions
import streamlit as st
from vector import process_and_store_files, search_relevant_chunks, fetch_company_info_from_link, get_openai_response, embedding_function, store_chunks, extract_text_from_file, read_document
from openai import OpenAI

from sklearn.metrics.pairwise import cosine_similarity
from transformers import GPT2Tokenizer
import numpy as np

api_key = "sk-taral-upwork-VqgjaTN5HZGDFmE9sIAAT3BlbkFJ8AkY3JurXEUjXh1cfnnj"
client = OpenAI(api_key=api_key)

tokenizer = GPT2Tokenizer.from_pretrained("gpt2")

history = {
    "audio_file": None,
    "transcript_text": None,
    "company_file": None,
    "final_questions_and_answers": None,
    "company_info_source": None
}

MAX_CONTEXT_LENGTH = 4096
MAX_FILE_SIZE = 25 * 1024 * 1024

def transcribe_audio(audio_file_path):
    with open(audio_file_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio_file, 
            response_format="text"
        )
    transcript_text = transcription.strip()
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

def truncate_text(text: str, max_length: int) -> str:
    tokens = tokenizer.encode(text)
    if len(tokens) > max_length:
        tokens = tokens[:max_length]
        text = tokenizer.decode(tokens)
    return text

def generate_answers(transcript, company_info, company_info_link, questions):
    combined_chunks = []

    if transcript:
        transcript_chunks = store_chunks(transcript, "transcript")
        combined_chunks.extend(transcript_chunks)

    if company_info:
        company_info_chunks = store_chunks(company_info, "company_info")
        combined_chunks.extend(company_info_chunks)

    if company_info_link:
        company_info_link_text = fetch_company_info_from_link(company_info_link)
        company_info_link_chunks = store_chunks(company_info_link_text, "company_info_link")
        combined_chunks.extend(company_info_link_chunks)

    print("Combined Chunks:")
    for chunk in combined_chunks:
        if 'metadata' in chunk and 'text' in chunk['metadata']:
            print(f"Chunk ID: {chunk['id']}, Text: {chunk['metadata']['text']}")  # Print entire chunk text
        else:
            print("Invalid chunk structure:", chunk)

    valid_chunks = [chunk for chunk in combined_chunks if 'metadata' in chunk and 'text' in chunk['metadata']]
    if not valid_chunks:
        print("No valid chunks found.")
        return []

    answers = []
    max_combined_length = 1024  
    for question in questions:
        sorted_chunks = sorted(valid_chunks, key=lambda chunk: similarity(chunk['metadata']['text'], question), reverse=True)
        context = ""
        for chunk in sorted_chunks:
            if len(context) + len(chunk['metadata']['text']) <= max_combined_length:
                context += chunk['metadata']['text'] + " "
            else:
                break
        context = truncate_text(context, max_combined_length)
        answer = get_openai_response(context, question)
        answers.append({"question": question, "answer": answer})
    return answers

from sklearn.metrics.pairwise import cosine_similarity

def similarity(text, question):
    question_embedding = embedding_function.embed_query(question)
    text_embedding = embedding_function.embed_documents([text])[0]
    return cosine_similarity([question_embedding], [text_embedding])[0][0]

def revise_answer(original_answer, instruction):
    prompt = f"""
    You are a helpful assistant. Please revise the given answer according to the provided instruction.

    Original answer:
    {original_answer}
    
    Instruction:
    {instruction}
    
    Revised answer:
    """

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": prompt}
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

def transcribe_and_analyze(audio_file, company_info, company_info_link, questions):
    transcript_text = ""
    company_info_text = ""

    if audio_file:
        audio_file_path = f"temp_{audio_file.name}"
        with open(audio_file_path, "wb") as f:
            f.write(audio_file.getbuffer())
        transcript_text = transcribe_audio(audio_file_path)

    if company_info:
        company_file_path = f"temp_{company_info.name}"
        with open(company_file_path, "wb") as f:
            f.write(company_info.getbuffer())
        filename, company_info_text, doc_hash = read_document(company_file_path, "PUBLIC")
        history["company_file"] = company_info.name
    elif company_info_link:
        company_info_text = fetch_company_info_from_link(company_info_link)

    answers = generate_answers(transcript_text, company_info_text, company_info_link, questions)
    return answers
