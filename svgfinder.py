import os
import requests
from bs4 import BeautifulSoup
import re

def get_svg_file(filename):
    """
    Check if SVG file exists locally, if not download it from svgrepo.com
    
    Args:
        filename (str): Name of SVG file (e.g., 'box.svg')
    
    Returns:
        str: Path to the SVG file
    """
    if not filename.endswith('.svg'):
        filename += '.svg'
    # Check if file exists locally
    if os.path.exists(filename):
        print(f"Found local file: {filename}")
        return filename
    
    # Extract the item name without .svg extension
    item = filename.split('.')[0]
    
    # Construct the URL
    url = f"https://www.svgrepo.com/vectors/{item}/multicolor/"
    
    try:
        # Make request to the website
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find elements with the specified class
        # Find first element with the specified class
        svg_element = soup.find(class_="style_NodeImage__FiBL5")
        svg_elements = [svg_element] if svg_element else []
        print(svg_elements)
        if not svg_elements:
            print(f"Could not find SVG for {item} on svgrepo.com")
            return None
        
        # Get the first SVG link
        for element in svg_elements:
            # Find the img tag within the element
            img_tag = element.find('img')
            if img_tag and img_tag.get('src'):
                svg_url = img_tag.get('src')
            
                if svg_url.endswith('.svg'):
                    # Download the SVG file
                    svg_response = requests.get(svg_url)
                    svg_response.raise_for_status()
                    
                    # Save to local file
                    with open(filename, 'wb') as f:
                        f.write(svg_response.content)
                    
                    print(f"Downloaded {filename} from {svg_url}")
                    return filename
        
        print(f"Could not find SVG link for {item} on svgrepo.com")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing svgrepo.com: {e}")
        return None
    

if __name__ == "__main__":
    # Example usage
    svg_filename = "cow.svg"
    svg_path = get_svg_file(svg_filename)
    if svg_path:
        print(f"SVG file is available at: {svg_path}")
    else:
        print("Failed to retrieve SVG file.")