"""
Image Generation Client using Replicate API.
"""
import os
import replicate
import requests
from typing import Optional
from io import BytesIO


class ImageClient:
    """Client for generating images using Replicate."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Image client.
        
        Args:
            api_key: Replicate API key. If None, will try to get from environment.
        """
        self.api_key = api_key or os.getenv("REPLICATE_API_TOKEN", "") or os.getenv("REPLICATE_API_KEY", "")
        if not self.api_key:
            raise ValueError("Replicate API key is required. Set REPLICATE_API_TOKEN or REPLICATE_API_KEY in .env file.")
        
        os.environ["REPLICATE_API_TOKEN"] = self.api_key
    
    def generate_image(
        self,
        prompt: str,
        model: str = "sundai-club/rachel_frenchie_mode:b07cb658fe2949e3fa1fa6f1f593f22e6cc62d6190eae8896fdc76ade752765b",
        guidance_scale: float = 2.0,
        model_type: str = "dev"
    ) -> Optional[str]:
        """
        Generate an image using Replicate.
        
        Args:
            prompt: The prompt for image generation
            model: The Replicate model to use
            guidance_scale: How much attention the model pays to the prompt (1-50)
            model_type: Model type ("dev" or "schnell")
            
        Returns:
            URL of the generated image, or None if generation failed
        """
        try:
            input_params = {
                "prompt": prompt,
                "guidance_scale": guidance_scale,
                "model": model_type
            }
            
            # For "dev" model, add num_inference_steps
            if model_type == "dev":
                input_params["num_inference_steps"] = 28
            
            output = replicate.run(model, input=input_params)
            
            # Output is typically a list, get first image URL
            if output:
                image_url = str(output[0])
                return image_url
            else:
                print("⚠️ No output from Replicate model")
                return None
                
        except Exception as e:
            print(f"Error generating image: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def download_image(self, image_url: str) -> Optional[BytesIO]:
        """
        Download an image from a URL.
        
        Args:
            image_url: URL of the image to download
            
        Returns:
            BytesIO object containing the image data, or None if download failed
        """
        try:
            response = requests.get(image_url, timeout=30)
            response.raise_for_status()
            return BytesIO(response.content)
        except Exception as e:
            print(f"Error downloading image: {e}")
            return None
