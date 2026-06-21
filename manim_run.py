import os
from google import genai
import subprocess
import boto3
import tempfile
from typing import List, Optional
import logging
import time
import re
import redis
import json
from gtts import gTTS
import uuid
from moviepy.editor import concatenate_audioclips, AudioFileClip, AudioClip,VideoFileClip
import numpy as np
from extract import markdown_to_plain_text
from dotenv import load_dotenv
from config import REDIS_HOST, REDIS_PORT, REDIS_DB
import asyncio
load_dotenv()
# Configure logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)



def manim_debugger(code:str, error_message: str):
    # finding error class:

    prompt=f"""
    Your task is to find the class name in which error is present. Find the class name used in manimcode.py

error message:
{error_message}

NO preambles or postmbles or explainations needed, return only class name in which error is present
if the error is not related to any class, return "the summary of error, exactly what is the reason for the error"

Examples:-
error : TypeError: Mobject.__getattr__.<locals>.getter() got an unexpected keyword argument 'edge'
output : Mobject

error : AttributeError: 'Camera' object has no attribute 'frame'
output : Camera

error : SvgFileNotFoundError: SVG file not found: doctor.svg
output : SVG File Not Found

"""
    
    client = genai.Client(api_key=os.getenv("GEMINI"))
    class_name = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt],
    ).text
    
    print(f"Debug: Error found in class: {class_name}")
    
    # Load Manim documentation
    try:
        with open("manim_documentation.json", "r") as doc_file:
            manim_doc = json.load(doc_file)
        
        # Get methods and attributes for the identified class
        class_info = manim_doc.get(class_name, {})
        methods = class_info.get("methods", [])
        attributes = class_info.get("attributes", [])
        
        # Prepare detailed prompt for fixing the code
        fix_prompt = f"""
You are a Manim debugging expert. I need help fixing an error in my code.

ERROR CLASS: {class_name}
ERROR MESSAGE: {error_message}

Here are the available methods and attributes for the {class_name} class:

METHODS:
{", ".join(methods)}

ATTRIBUTES:
{", ".join(attributes)}

ORIGINAL CODE:
{code}
Please provide a corrected version of the code, ensuring it adheres to Manim's best practices and resolves the error.
Don't make other changes unless necessary to fix the error.
If the error is related to svg not found, then please don't use that svg, and remove it from the code, and also remove the code related to that svg. Instead create something using manim classes, like Circle, Square, etc.
Return only the Manim code as a Python string, without any additional text or explanations.
```python
from manim import *
...rest of the code...
```
"""
        # Generate the fixed code using the model
        fixed_code = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[fix_prompt],
        ).text

        manim_code = re.sub(r'```python\n(.*?)\n```', r'\1', fixed_code, flags=re.DOTALL)
        # Save the generated code to a file
        with open("manimcode.py", "w") as file:
            file.write(manim_code)
        
        logger.info("Manim code generated successfully")
        return manim_code
    except Exception as e:
        logger.error(f"Error loading Manim documentation: {e}")
        return None



# Function 1: Generate Manim code using Google's generative AI
def generate_manim_code(
    animation_plan: str, 
    svg_paths: List[str], 
    api_key: str,
    model_name: str = "gemini-2.5-flash-preview-05-20"
) -> str:
    """
    Generate Manim code based on animation plan and SVG files using Google's generative AI.
    
    Args:   
        animation_plan: A string describing the animation plan
        svg_paths: List of paths to SVG files
        api_key: Google AI API key
        model_name: Model name to use
    
    Returns:
        Generated Manim code as a string
    """
    try:
        # Read Manim classes from file
        try:
            with open("manim_classes.txt", "r") as f:
                manim_classes = f.read().strip()
            logger.info("Successfully loaded Manim classes from file")
        except Exception as e:
            logger.error(f"Error loading Manim classes file: {str(e)}")
            manim_classes = ""  # Fallback to empty string if file not found
        # Configure the API
        client = genai.Client(api_key=api_key)
        svg_info = "\n".join([f"SVG file available at path: {path}" for path in svg_paths])
        user_prompt = f"Animation plan: {animation_plan}\n\nAvailable SVGs:\n{svg_info}"
        # Prepare the system prompt
        system_prompt = f"""
Goal: Convert a manim plan into a clean, bug-free, and highly visual Manim Python animation.

You are the Manim Coder Agent, a Manim expert that converts visual animation plans into actual Python Manim code.
You will receive one manim_plan string at a time. Your task is to:
Render all SVGs, graphs, texts, and diagrams.
Animate them based on the plan.
Use appropriate positions, scaling, and timing.
Ensure there are no overlaps or cluttered visuals.
Ensure each element is faded out or removed before a new scene starts.

Guidelines
Use SVGMobject for images (assume the SVG files are in the same folder).
Use Axes, NumberPlane, Line, Dot, and Graph for plotting graphs.
For LaTeX/math, use MathTex() or Tex() with correct scaling and positioning.
For code blocks or logic flows, use Code(), Rectangle(), or VGroup() with text.
Use .scale(), .move_to(), .to_edge(), .next_to(), and .shift() for positioning.
Use FadeIn, Write, Create, GrowArrow, Transform, and FadeOut animations.

Common Mistakes to Avoid
Don’t overwrite existing elements; fade them out first.
Avoid overlapping text and SVGs.
Don’t use self.add() without animation unless for static background.
Always add self.wait(x) after important transitions or narration timing (long texts).

The code should:
1. Import all necessary Manim modules
2. Define a single Scene class with a descriptive name
3. Implement the construct method with all required animations
4. All variables should be defined within the construct method


Available classes in manim module : - (don't use any class that is not in this list)
{manim_classes}

KEEP THE CODE SIMPLE, AND DO NOT USE ANY FANCY, ADVANCED MANIM FEATURES OR CUSTOM CLASSES, AS IT MAY LEAD TO ERRORS.
YOU HAVE TO BE 100% SURE THAT THE GENERATED CODE WILL RUN WITHOUT ANY ERRORS. SO USE ONLY THOSE CLASSES, METHODS, THAT YOU ARE SURE ABOUT.


Return only the Manim code as a Python string, without any additional text or explanations.
```python
from manim import *
...rest of the code...
```

user : {user_prompt}
"""

        # Prepare the user prompt with SVG information

        manim_code = client.models.generate_content(
            model=model_name,
            contents=[system_prompt],
        ).text
        # manim_code=groq_gen(system_prompt)
        # Clean up any "think" blocks from the generated code
        # manim_code = re.sub(r'<think>.*?</think>', '', manim_code, flags=re.DOTALL)
        manim_code = re.sub(r'```python\n(.*?)\n```', r'\1', manim_code, flags=re.DOTALL)
        # Save the generated code to a file
        with open("manimcode.py", "w") as file:
            file.write(manim_code)
        
        logger.info("Manim code generated successfully")
        return manim_code
    
    
    except Exception as e:
        logger.error(f"Error generating Manim code: {str(e)}")
        raise

# Function 2: Run the generated Manim code
def run_manim_code(class_name: str, code: str, recursion_depth: int = 0, max_recursion: int = 4, prev_error: str = "") -> str:
    """
    Run the generated Manim code and return the path to the output video.
    
    Args:
        class_name: The name of the Scene class to render
        code: The Manim code to run
        recursion_depth: Current recursion depth for debugging
        max_recursion: Maximum allowed recursion depth
    
    Returns:
        Path to the generated video file
    """
    try:
        # Run the Manim command
        command = f"manim -pql manimcode.py {class_name}"
        logger.info(f"Running command: {command}")
        
        result = subprocess.run(
            command, 
            shell=True, 
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60  # 5 minute timeout
        )
        
        logger.info(f"Manim execution output: {result.stdout}")
        
        # Find the generated video file (typically in media/videos/manimcode/480p15/)
        video_dir = os.path.join("media", "videos", "manimcode", "480p15")
        if not os.path.exists(video_dir):
            raise FileNotFoundError(f"Expected video directory not found: {video_dir}")
            
        video_files = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
        if not video_files:
            raise FileNotFoundError("No video files generated")
            
        # Get the most recent video file
        # Find the video file for the specific class_name
        target_file = f"{class_name}.mp4"
        video_path = os.path.join(video_dir, target_file)
        
        # Check if the file exists
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Expected video file not found: {video_path}")
        logger.info(f"Generated video at: {video_path}")
        
        return video_path
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to run Manim: \nstdout={e.stdout}\nstderr={e.stderr}")
        logger.error(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}")

        # Check recursion depth before trying to debug further
        if recursion_depth >= max_recursion:
            logger.error(f"Maximum recursion depth ({max_recursion}) reached. Giving up on debugging.")
            raise Exception(f"Failed to generate Manim video after {max_recursion} debugging attempts")
        last_line = e.stderr.splitlines()[-1]
        logger.info(f"Attempting debug iteration {recursion_depth + 1}/{max_recursion}")
        debugged_code = manim_debugger(code, last_line+"\nPrevious error:\n "+prev_error)
        return run_manim_code(class_name, debugged_code, recursion_depth + 1, max_recursion,prev_error=last_line)

    except subprocess.TimeoutExpired as e:
        print(f"Command timed out after {e.timeout} seconds")
        print(f"Partial stdout: {e.stdout if e.stdout else 'None'}")
        print(f"Partial stderr: {e.stderr if e.stderr else 'None'}")
        error_message = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode('utf-8', errors='replace') if e.stderr else "Command timed out with no error output")
        # Check recursion depth before trying to debug further
        error_message=str(error_message)
        if recursion_depth >= max_recursion:
            logger.error(f"Maximum recursion depth ({max_recursion}) reached. Giving up on debugging.")
            raise Exception(f"Failed to generate Manim video after {max_recursion} debugging attempts")
        last_line = error_message.splitlines()[-1]
        logger.info(f"Attempting debug iteration {recursion_depth + 1}/{max_recursion}")
        debugged_code = manim_debugger(code, last_line+"\nPrevious error:\n "+prev_error)
        return run_manim_code(class_name, debugged_code, recursion_depth + 1, max_recursion,prev_error=last_line)

    except Exception as e:
        logger.error(f"Error running Manim code: {str(e)}")
        raise

# Function 3: Upload the video to S3
def upload_to_s3(
    video_path: str,
    bucket_name: str,
    aws_access_key_id: Optional[str] = None,
    aws_secret_access_key: Optional[str] = None
) -> str:
    """
    Upload the generated video to an S3 bucket.
    
    Args:
        video_path: Path to the video file
        bucket_name: S3 bucket name
        aws_access_key_id: AWS access key ID (optional if using IAM roles)
        aws_secret_access_key: AWS secret access key (optional if using IAM roles)
        
    Returns:
        S3 key for the uploaded video
    """
    try:
        # Initialize S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        ) if aws_access_key_id and aws_secret_access_key else boto3.client('s3')
        
        # Generate a unique S3 key
        filename = os.path.basename(video_path)
        s3_key = f"manim_videos/{os.path.splitext(filename)[0]}_{int(time.time())}.mp4"
        
        # Upload the file
        s3_client.upload_file(
            Filename=video_path,
            Bucket=bucket_name,
            Key=s3_key,
            ExtraArgs={'ContentType': 'video/mp4'}
        )
        
        logger.info(f"Video uploaded to S3: bucket={bucket_name}, key={s3_key}")
        return s3_key
    
    except Exception as e:
        logger.error(f"Error uploading video to S3: {str(e)}")
        raise

# Main function that combines all steps
def create_manim_animation(
    animation_plan: str, 
    svg_paths: List[str], 
    # bucket_name: str,
    api_key: str,
    # aws_access_key_id: Optional[str] = None,
    # aws_secret_access_key: Optional[str] = None,
    output_dir: str,
    user_id: str,
    text: str,
    model_name: str = "gemini-2.5-flash-preview-05-20",
    narration_lang: str = "en",
    i=0
    

) -> str:
    """
    Create a Manim animation from a plan and SVGs, then upload it to S3.
    
    Args:
        animation_plan: A string describing the animation plan
        svg_paths: List of paths to SVG files
        bucket_name: S3 bucket name
        api_key: Google AI API key
        aws_access_key_id: AWS access key ID (optional if using IAM roles)
        aws_secret_access_key: AWS secret access key (optional if using IAM roles)
        model_name: Model name to use
        
    Returns:
        S3 key of the uploaded video
    """
    import time

    try:
        # 1. Generate Manim code
        manim_code = generate_manim_code(animation_plan, svg_paths, api_key, model_name)
        
        # Parse the class name from the generated code
        import re


        class_match = re.search(r"class\s+(\w+)\s*\(\s*\w+\s*\)", manim_code)
        print(f" Class match found: {class_match}")
        if not class_match:
            raise ValueError("Could not find Scene class name in generated code")
        class_name = class_match.group(1)
        logger.info(f"Found Scene class: {class_name}")
        
        # 2. Run the Manim code
        os.makedirs(output_dir, exist_ok=True)
        topic_name=str(output_dir).split("/")[-1]
        final_video_path = os.path.join(output_dir, f"manim_video_{user_id}_{uuid.uuid4()}.mp4")
        try:
            video_clip = None
            audio_clip = None
            try:
                video_path = run_manim_code(class_name=class_name, code=manim_code)
                # Get video duration
                video_clip = VideoFileClip(video_path)
                video_duration = video_clip.duration
            except Exception as e:
                logger.error(f"Error during Manim code execution: {str(e)}")

            # 3. Upload to S3
            # s3_key = upload_to_s3(video_path, bucket_name, aws_access_key_id, aws_secret_access_key)

            # 3. Generate audio from text
            logger.info(f"Generating audio from text using gTTS")
            audio_file = os.path.join(tempfile.gettempdir(), f"narration_{int(time.time())}.mp3")
            tts = gTTS(text=markdown_to_plain_text(text), lang="en", slow=False)
            tts.save(audio_file)
            logger.info(f"Audio saved to: {audio_file}")

            


            # Get audio duration
            audio_clip = AudioFileClip(audio_file)
            audio_duration = audio_clip.duration

            if video_clip:

                logger.info(f"Video duration: {video_duration}s, Audio duration: {audio_duration}s")

                # 5. Determine the target duration (use the longer of the two)
                target_duration = max(video_duration, audio_duration)

                # 6. Adjust media durations if needed
                # if abs(video_duration - audio_duration) > 0.5:  # If difference is significant
                if video_duration < audio_duration:
                    # Slow down video to match audio
                    logger.info(f"Extending video to match audio duration ({audio_duration}s)")
                    temp_adjusted_video = os.path.join(tempfile.gettempdir(), f"adjusted_video_{int(time.time())}.mp4")
                    speed_factor = video_duration / audio_duration
                    subprocess.run([
                        'ffmpeg', '-i', video_path, '-filter_complex',
                        f"setpts={1/speed_factor}*PTS", '-y', temp_adjusted_video
                    ], check=True)
                    video_path = temp_adjusted_video
                    video_clip = VideoFileClip(video_path)
                else:
                    logger.info(f"Extending audio to match video duration ({video_duration}s)")

                    silence_duration = video_duration - audio_duration

                    # Create silent clip with same FPS and sample rate
                    silence = AudioClip(make_frame=lambda t: np.zeros((1,)), duration=silence_duration)
                    silence = silence.set_fps(audio_clip.fps)

                    # Concatenate original audio with silence
                    extended_audio = concatenate_audioclips([audio_clip, silence])

                    # Save the new extended audio
                    temp_adjusted_audio = os.path.join(tempfile.gettempdir(), f"adjusted_audio_{int(time.time())}.mp3")
                    extended_audio.write_audiofile(temp_adjusted_audio)
                    
                    audio_file = temp_adjusted_audio
                    audio_clip = AudioFileClip(audio_file)

                message = {
                    "video_path": final_video_path,
                    "timestamp": time.time(),
                    "chunk_index": i,
                    "topic_name": topic_name,
                    "text_chunk": text,
                }
            else:
                logger.warning("No video clip generated, proceeding with audio only")
                message = {
                    "audio_path": audio_file,
                    "timestamp": time.time(),
                    "chunk_index": i,
                    "topic_name": topic_name,
                    "text_chunk": text,
                }
                

            
            
        except Exception as e:
            logger.error(f"Error during Manim code execution: {str(e)}")
            
        if video_clip:

            logger.info(f"Combining video and audio into final output: {final_video_path}")
            try:
                video_with_audio = video_clip.set_audio(audio_clip)
                video_with_audio.write_videofile(final_video_path, codec='libx264', audio_codec='aac')
            except Exception as audio_error:
                logger.error(f"Error adding audio to video: {str(audio_error)}")
                logger.info("Writing video without audio as fallback")
                if video_clip:
                    video_clip.write_videofile(final_video_path, codec='libx264')
                else:
                    logger.warning("No video clip available to write.")
            logger.info(f"Final video with narration saved to: {final_video_path}")

        # Clean up temporary files
        if video_clip:
            video_clip.close()
        if audio_clip:
            audio_clip.close()
        if 'temp_adjusted_video' in locals():
            os.remove(temp_adjusted_video)
        if 'temp_adjusted_audio' in locals():
            os.remove(temp_adjusted_audio)

        
        redis_client.xadd(f"workflow_{user_id}", message, maxlen=1000, approximate=True)

        return message  # Return the local path for now, can be changed to return S3 key later

    except Exception as e:
        logger.error(f"Failed to create Manim animation: {str(e)}")
        raise



# def groq_gen(msg):
#     from groq import Groq
    
#     client = Groq(api_key=os.getenv("GROQ"))
#     completion = client.chat.completions.create(
#         model="qwen-2.5-coder-32b",
#         messages=[
#             {
#                 "role": "user",
#                 "content": msg
#             }
#         ],
#         temperature=0.6,
#         top_p=0.95,
#         # reasoning_format="raw"
#     )
    
#     result_text = completion.choices[0].message.content 
    
    
#     return result_text




# Function to process text into audio chunks and send them to redis queue
async def text_to_audio_chunks(text_string: str, save_path: str="temp_audios", redis_queue_name: str = "audio_processing_queue", i=0,voice=True):
    """
    
    creates audio from text, and sends it to a Redis queue.

    Args:
        text_string: The text to be processed with #@#@# delimiters
        save_path: Directory path where audio files should be saved
        redis_queue_name: Name of the Redis queue to send audio paths

    Returns:
        List of generated audio file paths
    """

    try:
        
        
        # Create save directory if it doesn't exist
        if isinstance(save_path, str):
            os.makedirs(save_path, exist_ok=True)
        else:  # Assuming it's a pathlib.Path object
            save_path.mkdir(parents=True, exist_ok=True)
        
        # Split text by delimiter
        # chunks = text_string.split("#@#@#")
        # audio_paths = []
        
        # Process each chunk
        chunk=text_string
        # for i, chunk in enumerate(chunks):
        if not chunk.strip():
            logger.warning("Received an empty chunk, skipping audio generation.")
            return ""
            
        # Convert markdown to plain text
        plain_text = markdown_to_plain_text(chunk)
        

        
        print("generating audio for chunk: ", plain_text)
        if voice:
            
            # THEN GENERATE SMALLEST AUDIO FILE 
            # generating gtts audio (remove this if you want to integrate smallest ai)


            # Generate unique filename
            filename = f"audio_{i}_{uuid.uuid4().hex[:8]}.mp3"
            audio_path = os.path.join(save_path, filename)
            
            # Generate audio
            tts = gTTS(text=plain_text, lang='en')
            tts.save(audio_path)




        
            logger.info(f"Generated audio for chunk {i}: {audio_path}")
        else:
            audio_path=""
            await asyncio.sleep(0.1)
        # Send to Redis queue
        message = {
            "text_chunk": chunk,
            "audio_path": audio_path,
            "chunk_index": i+1,
            "timestamp": time.time(),
            "topic_name": str(save_path).split("/")[-1]  # Assuming save_path is structured like CONTENT/{book_name}/{chapter_title}/{topic_title_audio_chunks}/
        }

        # audio_paths.append(message)

        redis_client.xadd(redis_queue_name, message, maxlen=1000, approximate=True)
        # redis_client.rpush(redis_queue_name, json.dumps(message))
        logger.info(f"Processed chunk {i}, audio saved at: {audio_path}")
            
        return message   # save chunks in CONTENT/{book_name}/{chapter_title}/{topic_title_audio_chunks}/   and send from websocket by taking from this place only
        
    except Exception as e:
        logger.error(f"Error in text_to_audio_chunks: {str(e)}")
        raise



if __name__ == "__main__":
    try:
        with open("manimcode.py", "r") as file:
            manim_code = file.read()
            print("Content of manimcode.py:")
            print(manim_code)
    except FileNotFoundError:
        print("manimcode.py file not found")
    except Exception as e:
        print(f"Error reading manimcode.py: {str(e)}")
    run_manim_code("PlasmaTubeAnimation",manim_code)