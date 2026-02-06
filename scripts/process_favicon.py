import logging
import os

from PIL import Image, ImageDraw, ImageOps

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def process_favicon():
    input_path = os.path.join(os.getcwd(), "static", "images", "favicon.png")
    output_path = os.path.join(os.getcwd(), "static", "images", "favicon_circle.png")

    if not os.path.exists(input_path):
        logger.error(f"Error: {input_path} not found.")
        return

    try:
        img = Image.open(input_path).convert("RGBA")
        width, height = img.size

        # 1. Zoom/Crop: Determine the shortest side to make it square
        min_dim = min(width, height)

        # Calculate cropping box to center it
        left = (width - min_dim) / 2
        top = (height - min_dim) / 2
        right = (width + min_dim) / 2
        bottom = (height + min_dim) / 2

        # Crop to square center
        img = img.crop((left, top, right, bottom))

        # Resize to a standard icon size (e.g., 256x256 is good for high res, browser scales it down)
        size = (256, 256)
        img = img.resize(size, Image.Resampling.LANCZOS)

        # 2. Make it circular
        # Create a transparency mask
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)

        # Apply the mask
        result = ImageOps.fit(img, size, centering=(0.5, 0.5))
        result.putalpha(mask)

        # Save
        result.save(output_path, "PNG")
        logger.info(f"Successfully saved circular favicon to {output_path}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    process_favicon()
