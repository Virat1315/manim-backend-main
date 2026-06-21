
import logging
import os
import tempfile
import time
import os, time, tempfile, math, wave
from cloudinary.uploader import upload
from smallestai.waves import WavesClient  # Assuming the package is installed
# Helper Functions
TEMP_FOLDER= os.path.join(os.path.dirname(__file__), 'smallest')
def call_smallest_ai_api(client, client_params, max_retries=5, retry_delay=15):
    """Call the Smallest AI API with retry mechanism for rate limits"""
    logging.info("API Parameters:", {k: v for k, v in client_params.items() if k != 'text'})
    logging.info("")
    
    for attempt in range(max_retries):
        try:
            logging.info(f"API call attempt {attempt + 1}/{max_retries}")
            
            if 'text' not in client_params or 'save_as' not in client_params:
                logging.info("Missing required parameters: 'text' and 'save_as' must be provided", client_params)
                return False    
            
            if client_params.get('model') == 'lightning-large':
                consistency = client_params.get('consistency', 0.5)
                similarity = client_params.get('similarity', 0)
                enhancement = client_params.get('enhancement', True)
                
                result = client.synthesize(
                    text=client_params['text'],
                    save_as=client_params['save_as'],
                    model=client_params.get('model', 'lightning'),
                    voice_id=client_params.get('voice_id', 'emily'),
                    sample_rate=client_params.get('sample_rate', 24000),
                    speed=client_params.get('speed', 1.0),
                    consistency=consistency,
                    similarity=similarity,
                    enhancement=enhancement
                )
            else:
                result = client.synthesize(
                    text=client_params['text'],
                    save_as=client_params['save_as'],
                    model=client_params.get('model', 'lightning'),
                    voice_id=client_params.get('voice_id', 'emily'),
                    sample_rate=client_params.get('sample_rate', 24000),
                    speed=client_params.get('speed', 1.0)
                )
            
            print("Audio generated successfully!")
            return True
            
        except Exception as e:
            error_message = str(e)
            print(f"Error encountered: {error_message}")
            
            if "Rate limit exceeded" in error_message and attempt < max_retries - 1:
                wait_time = retry_delay * (attempt + 1)
                print(f"Rate limit hit. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                if "401" in error_message or "unauthorized" in error_message.lower():
                    print("API Key authentication failed. Please check your API key.")
                elif "404" in error_message or "not found" in error_message.lower():
                    print("Resource not found. The voice ID might be invalid. Check available voices with client.get_voices().")
                elif "429" in error_message:
                    print("Rate limit exceeded. Try again later or reduce request frequency.")
                else:
                    print(f"Smallest AI API Error: {error_message}")
                return False
    
    return False

def combine_wav_files(input_files, cloudinary_folder=None):
    """
    Combine multiple WAV files into a single WAV file
    
    Args:
        input_files (list): List of input WAV file paths
        output_file (str): Output WAV file path
    """
    if not input_files:
        print("No input files to combine.")
        return False
    
    try:
        with wave.open(input_files[0], 'rb') as first_file:
            params = first_file.getparams()

        # Create temporary output file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_out:
            output_path = temp_out.name

        with wave.open(output_path, 'wb') as output:
            output.setparams(params)
            for input_file in input_files:
                with wave.open(input_file, 'rb') as current_file:
                    if current_file.getparams() != params:
                        print(f"⚠️ File {input_file} has different parameters.")
                    output.writeframes(current_file.readframes(current_file.getnframes()))

        upload_options = {
            "resource_type": "video",
            "type": "authenticated",
        }
        if cloudinary_folder:
            upload_options["folder"] = cloudinary_folder

        print("Uploading to Cloudinary...")
        result = upload(output_path, **upload_options)

        # Clean up
        os.remove(output_path)

        return {
            "url": result['secure_url'],
            "public_id": result['public_id'],
            "original_filename": result['original_filename'],
            "duration": result['duration']
        }

    except Exception as e:
        print(f"❌ Error combining/uploading audio: {str(e)}")
        return None
    

def generate_audio(text, api_key, voice_id='emily', model='lightning', sample_rate=24000, speed=1.0, consistency=0.5, similarity=0, enhancement=True, max_text_length=1000, max_retries=5):
    """
    Generate audio from text using the Smallest AI API.
    
    Parameters:
        text (str): The text to convert to audio.
        api_key (str): The Smallest AI API key.
        voice_id (str): The voice ID to use (default: 'emily').
        model (str): The model to use ('lightning' or 'lightning-large').
        sample_rate (int): The sample rate for the audio (default: 24000).
        speed (float): Speed of the speech (default: 1.0).
        consistency (float): Consistency parameter for 'lightning-large' (default: 0.5).
        similarity (float): Similarity parameter for 'lightning-large' (default: 0).
        enhancement (bool): Enhancement for 'lightning-large' (default: True).
        max_text_length (int): Maximum length of text per API call (default: 1000).
        max_retries (int): Number of retry attempts for API calls (default: 3).
    
    Returns:
        bytes: The generated audio data.
    """
    logging.info(f"Generating audio for text: {text[:50]}... (truncated)")
    logging.info(f"Using API key: {api_key[:5]}... (truncated)")
    logging.info(f"Voice: {voice_id}, Model: {model}, Sample Rate: {sample_rate}, Speed: {speed}")
    if model == 'lightning-large':
        print(f"Advanced options: consistency={consistency}, similarity={similarity}, enhancement={enhancement}")
    
    try:
        client = WavesClient(api_key=api_key)
        logging.info("WavesClient initialized")
    except Exception as e:
        logging.error(f"Error initializing WavesClient: {str(e)}")
        raise
    
    # Break text into chunks if necessary
    chunks = []
    words = text.split()
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word)
        if current_length + word_length > max_text_length:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length + 1  # +1 for space
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    chunk_count = len(chunks)
    if chunk_count > 1:
        logging.info(f"Text will be processed in {chunk_count} chunks")
    
    temp_files = []
    try:
        os.makedirs(TEMP_FOLDER, exist_ok=True)
        logging.info(f"Temporary files will be stored in {TEMP_FOLDER}")
        for i, chunk in enumerate(chunks):
            fd, temp_path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)  # Close the file descriptor immediately
            temp_files.append(temp_path)
            
            client_params = {
                "text": chunk,
                "save_as": temp_path,
                "sample_rate": sample_rate,
                "speed": speed,
                "voice_id": voice_id,
                "model": model,
            }
            
            if model == "lightning-large":
                client_params["consistency"] = consistency
                client_params["similarity"] = similarity
                client_params["enhancement"] = enhancement
            
            logging.info(f"Processing chunk {i+1}/{chunk_count}...")
            success = call_smallest_ai_api(client, client_params, max_retries)
            if not success:
                logging.error(f"Failed to process chunk {i+1}")
                raise Exception("Audio generation failed")
            
            if i < chunk_count - 1:
                time.sleep(0.5)  # Delay between chunks

        logging.info("All audio chunks generated successfully!")
        
        cloudinary_result = combine_wav_files(
            input_files=temp_files,
            cloudinary_folder="audio_files",
        )

        if cloudinary_result:
            logging.info("Audio successfully combined and uploaded to Cloudinary!")
            return cloudinary_result
        else:
            raise Exception("Audio combination/upload failed.")
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        raise 
    finally:
        for f in temp_files:
            if os.path.exists(f):
                os.remove(f)
