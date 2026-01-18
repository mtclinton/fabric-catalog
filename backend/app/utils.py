import os
import aiohttp
import aiofiles
from urllib.parse import urlparse
import hashlib


async def download_image(image_url: str, fabric_name: str) -> str:
    """
    Download image from URL and save to static/images directory.
    
    Images are stored persistently in backend/static/images/ which is mounted
    as a volume, so they persist across container restarts.
    
    Args:
        image_url: Full URL of the image to download
        fabric_name: Name of the fabric (used in filename)
        
    Returns:
        Relative path to the saved image (e.g., "static/images/fabric_name_hash.jpg")
        or None if download failed
    """
    if not image_url:
        return None
    
    # Create images directory if it doesn't exist
    # This directory is mounted as a volume for persistence
    images_dir = "static/images"
    os.makedirs(images_dir, exist_ok=True)
    
    # Generate unique filename from fabric name and URL hash
    url_hash = hashlib.md5(image_url.encode()).hexdigest()[:8]
    safe_name = "".join(c for c in fabric_name if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
    safe_name = safe_name.replace(' ', '_')
    
    # Get file extension from URL or default to .jpg
    parsed_url = urlparse(image_url)
    ext = os.path.splitext(parsed_url.path)[1] or ".jpg"
    # Clean extension (remove query params if any)
    ext = ext.split('?')[0] if '?' in ext else ext
    
    filename = f"{safe_name}_{url_hash}{ext}"
    filepath = os.path.join(images_dir, filename)
    
    # Skip if already downloaded
    if os.path.exists(filepath):
        print(f"Image already exists: {filepath}")
        return filepath
    
    try:
        print(f"Downloading image from {image_url}...")
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    # Check content type to ensure it's an image
                    content_type = response.headers.get('Content-Type', '')
                    if not content_type.startswith('image/'):
                        print(f"Warning: {image_url} doesn't appear to be an image (Content-Type: {content_type})")
                    
                    # Download and save image
                    async with aiofiles.open(filepath, 'wb') as f:
                        await f.write(await response.read())
                    print(f"Image saved to {filepath}")
                    return filepath
                else:
                    print(f"Failed to download image: HTTP {response.status}")
    except Exception as e:
        print(f"Error downloading image {image_url}: {e}")
        return None
    
    return None
