import os
from pathlib import Path
from google import genai
from dotenv import load_dotenv
load_dotenv()
from manim_run import create_manim_animation, text_to_audio_chunks
from animation_plan import generate_animation_plan
from extract import trim_pdf
import json
from celery import Celery
import asyncio
import time
import re
from config import REDIS_URL

celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

# Support running Celery tasks eagerly for local testing without a Redis broker.
if os.getenv("CELERY_TASK_ALWAYS_EAGER", "0") == "1":
    celery_app.conf.task_always_eager = True

@celery_app.task
def pcc(chapter_data, pdf_page_for_book_page_1, mode, previous_knowledge, education_level, language, book_name, user_id,pdf_path,voice):
    asyncio.run(process_chapter_content(chapter_data, pdf_page_for_book_page_1, mode, previous_knowledge, education_level, language, book_name, user_id,pdf_path,voice))


# create another func for others processing


async def process_chapter_content(chapter_data, pdf_page_for_book_page_1, mode="deep dive", 
                          previous_knowledge="", education_level="12th studying", language="english", book_name=None,user_id="default",pdf_path=None,voice=True):
    """
    Process chapter content from a PDF based on provided structure and learning parameters.
    
    Args:
        chapter_data: List containing chapter title and topics with page numbers
        pdf_page_for_book_page_1: PDF page number corresponding to book page 1
        mode: Learning mode - "deep dive", "revise", or "exam"
        previous_knowledge: User's existing knowledge of the topic
        education_level: User's education level (e.g. "10th pass", "12th studying")
        language: Preferred language for content (english/hindi/hinglish)
    
    Returns:
        Dictionary containing generated content for each topic
    """
    # Configure Gemini API
    client = genai.Client(api_key=os.getenv("GEMINI"))
    
    full_pdf_path=pdf_path
    # Extract chapter title and topics
    chapter_title = chapter_data[0]
    topics_dict = chapter_data[1]
    
    # Create output directory
    # output_dir = Path(f"CONTENT/{book_name.replace('.', '_')}/{chapter_title.replace(':', '_').replace(' ', '_')}")
    # output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define mode-specific prompts
    mode_prompts = {
        "deep dive": """
            Please provide an in-depth explanation of this topic. Include:
            - Detailed theoretical concepts with clear analogies and examples
            - Real-world applications and significance
            - Interconnections with related concepts
            - Common misconceptions and how to avoid them
            - keep content well descriptive and comprehensive
        """,
        
        "revise": """
            Please focus on exam preparation for this topic. Include:
            - Brief explanations of key concepts , real world applications, formulas
            - Common question patterns and how to approach them
            - Quick revision points for last-minute study
            - just give a small line overview for non important / theoretical topics
            - keep the content short
        """
    }
    
    # Get sorted topics with page numbers to determine page ranges
    sorted_topics = []
    for topic, page in topics_dict.items():
        try:
            book_page = int(page)
            pdf_page = book_page + pdf_page_for_book_page_1 - 1
            sorted_topics.append((topic, book_page, pdf_page))
        except ValueError:
            print(f"Warning: Invalid page number for topic '{topic}': {page}")
    
    # Sort topics by book page number
    # sorted_topics.sort(key=lambda x: x[1])
    print(sorted_topics)
    
    results = {}
    
    # Process each topic
    for i, (topic, book_page, pdf_page) in enumerate(sorted_topics):
        output_dir = Path(f"CONTENT/{user_id}/{book_name.replace('.', '_')}/{chapter_title.replace(':', '_').replace(' ', '_')}/AUDIO_VIDEO_{topic.replace(':', '_').replace(' ', '_')}")
        output_dir.mkdir(parents=True, exist_ok=True)   
        print(f"Processing: {topic} (Page {book_page})")
        
        # Determine end page for this topic
        if i < len(sorted_topics) - 1:
            next_pdf_page = sorted_topics[i + 1][2]
        else:
            # If it's the last topic, add a reasonable number of pages
            next_pdf_page = pdf_page + 1
        
        # Create trimmed PDF for this topic
        trimmed_pdf_path = trim_pdf(
            pdf_path=full_pdf_path,
            start_page=pdf_page,
            end_page=next_pdf_page,
            output_path=str(output_dir / f"{topic.replace(':', '_').replace(' ', '_')}.pdf")
        )
        
        # Build the prompt for Gemini
        prompt = f"""
        I want you to act as an expert teacher explaining the topic: {topic} from {chapter_title}.
        
        Mode: {mode}
        {mode_prompts.get(mode.lower())}
        
        Student's previous knowledge: {previous_knowledge}
        
        Education level: {education_level}
        
        Please explain in {language} language.
        
        Use the provided PDF content to create a comprehensive lesson for the given topic only. Focus on making the concepts clear and engaging. Explaination should be interactive and appropriate according to student's education level.
        The full explaination have to be divided into several chunks. one chunk can either be a simple text streaming, whose voiceover will be played to the user, or it will be a manim animation video with voiceover
        A chunk should be simple if it is just theory and cannot be visualized easily. the chunk should be manim only if it can be visualized interactively. Try to keep less manim chunks (if there are total 10 chunks then keep at max only 2 manim chunks and rest simple text streaming chunks).
        The manim chunks should be long enough, complete and meaningful. Right now keep the manim chunk long enough to cover ONE complete concept or example. (dont give manim code. give only the detailed explaination of the concept or question or answer in manim chunk)
        one simple chunk will be shown to the user with it's voiceover at a time, so that the user can understand the content in a more interactive way. the length of simple text streaming chunk can vary according to the need or complexity of the topic or user's preferences.
        IMPORTANT : STRICTLY keep the content and the formulas in proper markdown format !!, so that it can be beautifully and properly rendered in the frontend. Use all the mathematical symbols and notations properly in markdown, also use proper headings and subheadings, tables to make the content more readable.
        If pdf contains list of short objective questions -> so use simple text streaming chunks for each to explain the questions and their answers.
        If pdf contains list of solved numerical examples -> so use manim chunk for some of them if the question is long or visually appealing, else use several simple text streaming chunks to explain the question and it's answer.
        if pdf contains list of only theoretical questions without explainations -> so use simple text streaming chunks to save the questions and short explaination. (one chunk per question)
        I want you to return the explaination in below format:

#####SIMPLE#####
<SIMPLE CHUNK CONTENT : explaination according to user's preferences for scene 1>
#####MANIM#####
<MANIM CHUNK CONTENT : explaination according to user's preferences for scene 2 (don't give code, just give detailed explaination of concept/question/answer)>
#####SIMPLE#####
<more SIMPLE CHUNK CONTENT : explaination according to user's preferences for scene 3>

........all scenes will be in this format
        No preambles or postambles are required, just return the content in the above format.
"""
        
        # # Upload file to Gemini and generate content
        # max_retries = 3
        # retry_count = 0
        
        # while retry_count < max_retries:
        try:
            try:
                with open(trimmed_pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                
                # Generate content using a regular prompt instead of system prompt
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=[
                        {
                            "mime_type": "application/pdf",
                            "data": pdf_bytes
                        },
                        prompt
                    ],
                )
            except Exception as e:
                print("gemini upload file or generating error:", e)

            
            response_text = response.text
            # Parse the response text to extract simple and manim chunks
            chunks = re.findall(r'#####(SIMPLE|MANIM)#####\s*([\s\S]*?)(?=#####|$)', response_text)

            # Create a list of dictionaries for each chunk
            topics_dict = []
            for chunk_type, content in chunks:
                chunk = {
                    "type": chunk_type.lower(),
                    "content": content.strip()
                }
                topics_dict.append(chunk)

            # If no chunks were found, create a basic structure with the whole content
            if not topics_dict:
                topics_dict = [{
                    "type": "simple",
                    "content": response_text.strip()
                }]







            # if response_text[0] == "`":
            #     response_text = response_text.replace("```json", "").replace("```", "")
            # # Extract JSON from response using a more robust method
            # print(f"Gemini response for topic '{topic}': {response_text}")
            # json_content = response_text
            
            
            # try:
            #     topics_dict = eval(json_content)
            # except json.JSONDecodeError as e:
            #     print(f"JSON parse error for '{topic}': {e}")
            #     print(f"Problematic JSON content: {json_content}")
                
            #     # Try fixing common JSON errors
            #     try:
            #         # Replace single quotes with double quotes
            #         fixed_content = json_content.replace("'", '"')
            #         topics_dict = json.loads(fixed_content)
            #     except json.JSONDecodeError:
            #         # If still failing, create a basic structure to continue
            #         topics_dict = [{
            #             "content": f"Content generation failed for {topic}. Please try again.",
            #             "type": "simple",
            #         }]
            # print(f"Generated content for '{topic}': {topics_dict}")




        except Exception as e:
            print(f"Failed to generate content for '{topic}': {str(e)}")
            topics_dict = [{
                "type": "simple",
                "content": f"Content generation failed : {str(e)}"
            }]
        
         # Save content to file
        # output_dir = Path(f"CONTENT/{book_name.replace('.', '_')}/{chapter_title.replace(':', '_').replace(' ', '_')}/AUDIO_VIDEO_{topic.replace(':', '_').replace(' ', '_')}")
        output_file = output_dir / f"{topic.replace(':', '_').replace(' ', '_')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(topics_dict, f, ensure_ascii=False, indent=4)
                
        try:
            
            all_paths = []
            for i, chunk in enumerate(topics_dict):
                if chunk.get("type") == "simple":
                    audio_path_with_text = await text_to_audio_chunks(chunk["content"], output_dir, f"workflow_{user_id}", i,voice)
                    all_paths.append(audio_path_with_text)
                elif chunk.get("type") == "manim":
                    example=chunk.get("content", "")
                    animation_plan=generate_animation_plan(numerical=example,narration_lang=language)
                    # animation_with_audio=[]
                    print("Broken into,", len(animation_plan), "scenes")
                    for j,scene in enumerate(animation_plan):
                        print(f"Creating Manim animation for scene {i+1}, manimscene {j+1} of topic '{topic}'")
                        # Create Manim animation for each scene
                        # find svg if not present in directory, then download it from the internet
                        try:
                            manim_animation_msg = create_manim_animation(
                                animation_plan=scene["manim_plan"],
                                svg_paths=scene.get("images", []),
                                api_key=os.getenv("GEMINI"),
                                narration_lang=language,
                                output_dir=output_dir,
                                user_id=user_id,
                                text=scene["text"],
                                i=f"{i+1}:{j+1}",
                            )
                            all_paths.append(manim_animation_msg)
                            # manim_animation_path = manim_animation_msg.get("video_path", None)
                        except Exception as e:
                            print(f"Error creating Manim animation for scene {i+1}, manimscene {j+1} of topic '{topic}': {e}")
                            # manim_animation_path = None
                            
                        # animation_with_audio.append(manim_animation_path)
                    # all_paths.append({
                    #     "example_or_question": example,
                    #     "animation_paths": animation_with_audio
                    # })
            # Save audio paths with text to file
            # output_dir.mkdir(parents=True, exist_ok=True)
            # audio_json_path = output_dir / "audio_paths_with_text.json"
            # with open(audio_json_path, 'w', encoding='utf-8') as f:
            #     json.dump(audio_paths_with_text, f, ensure_ascii=False, indent=4)

            # Save all paths to a single JSON file
            animations_json_path = output_dir / "all_paths.json"
            with open(animations_json_path, 'w', encoding='utf-8') as f:
                json.dump(all_paths, f, ensure_ascii=False, indent=4)

            results[topic] = topics_dict
            print(f"✓ Generated content for '{topic}'")

        except Exception as e:
            print(f"Error processing post-generation steps for '{topic}': {e}")
            results[topic] = f"Error: {str(e)}"
    
    return results








# Example usage:
if __name__ == "__main__":
    sample_chapter_data = [
        "Chapter 23: Heat and Temperature",
        {
            "23.1 Hot and Cold Bodies": "1",
            "23.2 Zeroth Law of Thermodynamics": "1",
            "23.3 Defining Scale of Temperature: Mercury and Resistance Thermometers": "1",
            "23.4 Constant Volume Gas Thermometer": "3",
            "23.5 Ideal Gas Temperature Scale": "5",
            "23.6 Celsius Temperature Scale": "5",
            "23.7 Ideal Gas Equation": "5",
            "23.8 Callender's Compensated Constant Pressure Thermometer": "5",
            "23.9 Adiabatic and Diathermic Walls": "6",
            "23.10 Thermal Expansion": "6",
            "Worked Out Examples": "7",
            "Questions for Short Answer": "11",
            "Objective I": "11",
            "Objective II": "12",
            "Exercises": "12"
        }
    ]
    
    # Set your PDF path and relevant page number here
    pdf_page_for_book_page_1 = 17  # Example value - adjust as needed
    full_pdf_path = "/home/aryan/deep-spark-mentor-ai/backend/Concepts_of_Physics_Vol_2_2023_Edition.pdf"  # Replace with actual path
    
    results = process_chapter_content(
        sample_chapter_data,
        pdf_page_for_book_page_1,
        full_pdf_path,
        mode="last minute exam",
        previous_knowledge="studied nothing in class 11th. just passed",
        education_level="12th studying",
        language="hinglish"
    )