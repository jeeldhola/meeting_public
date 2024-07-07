import os
from docx import Document
from gtts import gTTS

def read_text_from_docx(file_path: str) -> str:
    """
    Reads text from a DOCX file and returns it as a single string.

    :param file_path: Path to the DOCX file
    :return: Text content of the DOCX file
    """
    doc = Document(file_path)
    full_text = []
    for paragraph in doc.paragraphs:
        full_text.append(paragraph.text)
    return '\n'.join(full_text)

def convert_text_to_speech(text: str, output_file: str):
    """
    Converts text to speech and saves it as an MP3 file.

    :param text: Text to be converted to speech
    :param output_file: Path to the output MP3 file
    """
    tts = gTTS(text)
    tts.save(output_file)

def main():
    input_file = "C:\\Users\\admin\\Desktop\\Mindlytic\\Meeting Analysis\\audio_files\\Grant Transcript Example.docx"
    output_file = 'C:\\Users\\admin\\Desktop\\Mindlytic\\Meeting Analysis\\audio_files\\grant_transcript_example.mp3'  
    text = read_text_from_docx(input_file)

    convert_text_to_speech(text, output_file)
    
    print(f"MP3 file has been created: {output_file}")

if __name__ == '__main__':
    main()
