from typing import List, Dict, Any, Callable, Optional
from skills.base import BaseSkill
from tools import image
from tools.schemas import IMAGE_TOOL_SCHEMAS


class ImageGenSkill(BaseSkill):
    name = "image_gen"
    display_name = "AI Image Generator"
    description = "Generate high-resolution creative images from descriptive text prompts and render them directly in the chat interface."
    icon = "Image"
    version = "1.0.0"
    is_core = False
    enabled_by_default = True

    task_categories = ["vision", "general"]
    trigger_keywords = [
        "generate image", "create image", "draw", "picture of", "illustration",
        "render image", "generate a photo", "make an image", "wallpaper"
    ]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return IMAGE_TOOL_SCHEMAS

    def get_tool_registry(self) -> Dict[str, Callable]:
        return {
            "generate_image": image.generate_image,
        }

    def get_prompt_instructions(self) -> Optional[str]:
        return (
            "IMAGE GENERATION GUIDELINES:\n"
            "- When asked to generate, create, or draw an image, call 'generate_image' with a descriptive visual prompt.\n"
            "- Never open external browser windows for images."
        )
