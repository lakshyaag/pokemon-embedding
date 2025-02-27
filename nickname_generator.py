import base64
import io
from typing import List
from PIL import Image
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field


class Nicknames(BaseModel):
    """
    Pydantic model for structured output from the LLM.
    """
    nicknames: List[str] = Field(
        description="A list of words that reflect possible nicknames for the sprite",
    )


def convert_image_to_base64(image: Image.Image) -> str:
    """
    Convert a PIL Image to a base64 encoded string.
    
    Args:
        image: The PIL Image to convert
        
    Returns:
        A base64 encoded string of the image
    """
    # Convert PIL Image to bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format=image.format or 'PNG')
    img_bytes = img_byte_arr.getvalue()

    return base64.b64encode(img_bytes).decode("utf-8")


def get_nicknames(pokemon_name: str, display_image: bool = False) -> List[str]:
    """
    Get nicknames for a Pokémon using the OpenAI API.
    
    Args:
        pokemon_name: The name of the Pokémon
        display_image: Whether to display the image (useful in notebooks)
        
    Returns:
        A list of nicknames for the Pokémon
    """
    # Load the Pokémon image
    try:
        pokemon_image = Image.open(f"sprites/{pokemon_name}_combined.png")
    except FileNotFoundError:
        raise ValueError(f"No sprite found for Pokémon: {pokemon_name}")
    
    # Convert the image to base64
    pokemon_image_b64 = convert_image_to_base64(pokemon_image)
    
    # Display the image if requested
    if display_image:
        try:
            from IPython.display import display
            display(pokemon_image)
        except ImportError:
            pass  # Not in a notebook environment
    
    # Initialize the OpenAI model
    model = ChatOpenAI(model="gpt-4o", temperature=0.7)
    
    # Create the messages for the API call
    messages = [
        SystemMessage(
            """
            Please provide a list of 5 words from the English dictionary for this sprite that reflect possible nicknames. 
            Each word should be a single word and be appropriate for a nickname.
            """
        ),
        HumanMessage(
            [
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{pokemon_image_b64}"},
                }
            ]
        ),
    ]
    
    # Get the response from the API
    response = model.with_structured_output(Nicknames).invoke(messages)
    
    return response.nicknames 