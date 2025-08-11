from PIL import Image, ImageDraw, ImageFont, ImageFilter
import random
import string
import os
import numpy as np

def generate_serial():
    """Generates a random 12-character Apple-style serial number."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

def add_noise(image):
    """Adds random 'salt and pepper' noise to an image."""
    np_img = np.array(image)
    noise = np.random.randint(0, 50, np_img.shape, dtype='uint8')
    np_img = np.clip(np_img + noise, 0, 255)
    return Image.fromarray(np_img)

def create_synthetic_image(serial, file_path, font_path=None, font_size=48, distortions=None):
    """
    Creates a synthetic image with a given serial number and applies optional distortions.
    """
    img_width, img_height = 400, 100
    bg_color = (255, 255, 255)  # White background
    text_color = (0, 0, 0)      # Black text

    image = Image.new('RGB', (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(image)

    # Load a default or specified font
    try:
        if font_path and os.path.exists(font_path):
            font = ImageFont.truetype(font_path, font_size)
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    # Get text size and center it
    bbox = font.getbbox(serial)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (img_width - text_width) / 2
    y = (img_height - text_height) / 2
    draw.text((x, y), serial, font=font, fill=text_color)

    # Apply distortions if any are specified
    if distortions:
        if 'blur' in distortions:
            image = image.filter(ImageFilter.GaussianBlur(radius=distortions['blur']))
        if 'rotate' in distortions:
            image = image.rotate(distortions['rotate'], expand=True, fillcolor=bg_color)
        if 'noise' in distortions and distortions['noise']:
            image = add_noise(image)

    image.save(file_path)

if __name__ == '__main__':
    # Directory to save images
    output_dir = 'synthetic_test_images'
    os.makedirs(output_dir, exist_ok=True)

    # Define the types of sample images to generate
    samples = [
        {'distortions': {}, 'label': 'clean'},
        {'distortions': {'blur': 2}, 'label': 'blur'},
        {'distortions': {'rotate': 10}, 'label': 'rotate'},
        {'distortions': {'blur': 1, 'rotate': -5}, 'label': 'blur_rotate'},
        {'distortions': {'noise': True}, 'label': 'noise'}
    ]

    print(f"Generating {len(samples)} synthetic images in '{output_dir}/'...")

    for i, sample in enumerate(samples):
        serial = generate_serial()
        distortions = sample['distortions']
        label = sample['label']
        
        filename = f'synthetic_{i+1:02d}_{label}_{serial}.png'
        filepath = os.path.join(output_dir, filename)
        
        create_synthetic_image(serial, filepath, distortions=distortions)
        print(f"Created: {filepath}")

    print("Done.")

