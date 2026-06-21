import re

# svg finder, text to voice.

def find_scene_classes(file_path="manimcode.py"):
    """
    Find all class names that inherit from Scene in the given file.
    
    Args:
        file_path (str): Path to the file to search in
        
    Returns:
        list: List of class names inheriting from Scene
    """
    try:
        with open(file_path, 'r') as file:
            manim_code = file.read()
            
        scene_classes = []
        pattern = r"class\s+(\w+)\s*\(\s*\w+\s*\)"
        matches = re.search(pattern, manim_code)
        print(matches)
        if matches:
            scene_classes.append(matches.group(1))

        return scene_classes
    except Exception as e:
        print(f"Error reading or parsing {file_path}: {e}")
        return []
    
if __name__ == "__main__":
    # Example usage
    # Assuming 'manimcode.py' is the file containing the Manim code
    # Uncomment the line below to run the function and print the results
    print(find_scene_classes())
    





