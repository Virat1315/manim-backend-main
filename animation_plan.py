import os
import json
from google import genai
from typing import List, Dict, Any
from dotenv import load_dotenv
from svgfinder import get_svg_file
load_dotenv()
def setup_genai(api_key: str = None) -> genai.Client:
    """Set up the Google GenerativeAI with API key."""
    if api_key is None:
        api_key = os.environ.get("GEMINI")
        if api_key is None:
            raise ValueError("API key not provided and not found in environment variables")
    
    return genai.Client(api_key=api_key)




def generate_animation_plan(numerical: str, api_key: str = None,narration_lang: str = "english") -> List[Dict[str, Any]]:
    """
    Generate a Manim animation plan for a given topic using Google's Generative AI.
    
    Args:
        topic (str): The topic to create animations for (book explanation, slide explanation, etc.)
        api_key (str, optional): Google API key. If not provided, looks for GOOGLE_API_KEY env variable.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries, each containing:
            - manim_animation_plan: Plan for Manim animation
            - text_explanation: Text to be converted to voice
            - required_svgs: List of SVGs needed for the animation
    """
    # Setup Google GenerativeAI
    client = setup_genai(api_key)

    # Create the prompt
    system_prompt = f"""
    
You are the Manim Planner Agent, a visual content designer for educational animations. You receive an example or question explanation (e.g., a math problem, a physics concept). Your job is to break it into some animation scenes that are:

Visually engaging, Realistic (where applicable) , complete and independent, Synchronized with voiceover narration
Your response must be a list of JSON objects, where each object includes:

🔹 "text" (string)
This is the spoken narration for the scene. It will be converted to audio and played alongside the animation.
narration_language is {narration_lang}. Keep the narration clear, concise, and engaging. Use simple language appropriate for the target audience (e.g., school/college students).
This maybe long, but should be comprehensive and clear. The manim animation will be slowed down and synced with this narration.

🔹 "manim_plan" (string) (keep in english only)
A detailed visual plan for how the scene will look. Describe:

Positioning of elements (center, top-left, etc.)
characters (e.g., person running, cloud, bus)
Mathematical visuals (number lines, graphs, equations)
Code snippets (if explaining programming logic)
Diagrams or geometric shapes
Animations (fade in, shift, draw, transform, arrow movement, growing graphs)
Pacing (e.g., wait for 2 seconds after text appears)

Always include:

Transitions between steps
Clearing or fading out previous elements (avoid clutter or text overlap)

🔹 "images" (list of strings)
List of required SVGs or visual assets used in manim plan. These can include:
Real-life image names like "cloud.svg", "bus.svg"
(this should STRICTLY! be one word and very commonly used SVGs like man, bus, etc., avoid complex or uncommon SVGs)

the final output will be a list of JSON objects, each containing the above fields.
Don't create so many scenes (JSON objects) that it becomes overwhelming. Aim for at most 3 scenes, focusing on clarity , engagement and self-completeness in each scene.

output format:-
[
{{
  "text": "The Pythagorean Theorem states that in a right triangle, the square of the length of the hypotenuse is equal to the sum of the squares of the lengths of the other two sides.",
  "manim_plan": "Create a right triangle with labeled sides a, b, and c. Show the equation a^2 + b^2 = c^2.",
  "images": [ "triangle.svg"]
}},
{{
  "text": "In this scene, we will explore the concept of velocity.",
  "manim_plan": "Create a number line to represent time. Place a dot on the line to represent the object's position at different times. Use arrows to show the direction of motion.",
  "images": ["line.svg", "arrow.svg"]
}}
]


Additional Guidelines :-
SVG images should have very simple one word names.
Strictly Use very commonly available SVGs.

For math problems:
Represent graphs with axes and labels.
Place equations using LaTeX formatting.
Use point plotting and vector arrows when applicable.

For programming:
Show flowcharts, visual variable tracking, code snippets in rounded boxes.

Ensure no elements overlap unless intentionally animated.


QUESTION: {numerical}

No preambles or postambles are required. Just provide the JSON output as described above. Keep strings in double quotes, avoid escape characters, and ensure the JSON is valid.

    """


    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents=[system_prompt],
    )
    
    # Parse the response
    try:
        # Try to find JSON content in the response
        content = response.text
        
        # Extract JSON content if embedded in markdown or other text
        if "```json" in content:
            json_content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_content = content.split("```")[1].strip()
        else:
            json_content = content
            
        # Parse the JSON
        
        animation_plans = json.loads(json_content)
        for plan in animation_plans:
            loop=plan.get("images", [])
            for svg in loop:
                svgimg=get_svg_file(svg)  # Ensure SVG files are downloaded or available
                if svgimg is None:
                    plan["images"].remove(svg)  # Remove if SVG not found

                

                
        return animation_plans
    
    except Exception as e:
        # If parsing fails, return a simplified structure with the error and raw response
        print(f"Error parsing response: {e}")
        return [{
            "scene_id": "error_scene",
            "manim_animation_plan": "Error processing animation plan",
            "text_explanation": f"Error: {str(e)}. Please try again with a different topic or formatting.",
            "required_svgs": [],
            "raw_response": response.text
        }]

# Example usage
if __name__ == "__main__":
    # Set your API key here or in environment variables
    # os.environ["GOOGLE_API_KEY"] = "your-api-key"
    
    test_topic = "The Pythagorean Theorem"
    animation_plans = generate_animation_plan(test_topic)
    
    print(json.dumps(animation_plans, indent=2))
