"""
Static File Optimization for ASOUD Platform
"""

import os
import logging
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
try:
    from PIL import Image
except ImportError:
    Image = None
import hashlib
import mimetypes

logger = logging.getLogger(__name__)

class ImageOptimizer:
    """
    Image optimization utilities
    """
    
    SUPPORTED_FORMATS = ['JPEG', 'PNG', 'WEBP']
    QUALITY_SETTINGS = {
        'high': 95,
        'medium': 85,
        'low': 75,
        'thumbnail': 80
    }
    
    def __init__(self):
        self.upload_path = getattr(settings, 'MEDIA_ROOT', 'media')
        self.static_path = getattr(settings, 'STATIC_ROOT', 'static')
    
    def optimize_image(self, image_path, quality='medium', max_width=None, max_height=None, format='JPEG'):
        """Optimize image with specified parameters"""
        if Image is None:
            logger.warning("PIL not available, skipping image optimization")
            return None
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if dimensions specified
                if max_width or max_height:
                    img.thumbnail((max_width or img.width, max_height or img.height), Image.Resampling.LANCZOS)
                
                # Get quality setting
                quality_value = self.QUALITY_SETTINGS.get(quality, 85)
                
                # Create optimized image
                optimized_path = self._get_optimized_path(image_path, quality, format)
                
                # Save optimized image
                img.save(optimized_path, format=format, quality=quality_value, optimize=True)
                
                logger.info(f"Image optimized: {image_path} -> {optimized_path}")
                return optimized_path
                
        except Exception as e:
            logger.error(f"Error optimizing image {image_path}: {e}")
            return None
    
    def create_thumbnail(self, image_path, size=(150, 150), quality='thumbnail'):
        """Create thumbnail for image"""
        if Image is None:
            logger.warning("PIL not available, skipping thumbnail creation")
            return None
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                
                # Get quality setting
                quality_value = self.QUALITY_SETTINGS.get(quality, 80)
                
                # Create thumbnail path
                thumbnail_path = self._get_thumbnail_path(image_path, size)
                
                # Save thumbnail
                img.save(thumbnail_path, format='JPEG', quality=quality_value, optimize=True)
                
                logger.info(f"Thumbnail created: {image_path} -> {thumbnail_path}")
                return thumbnail_path
                
        except Exception as e:
            logger.error(f"Error creating thumbnail {image_path}: {e}")
            return None
    
    def create_responsive_images(self, image_path):
        """Create responsive images for different screen sizes"""
        if Image is None:
            logger.warning("PIL not available, skipping responsive image creation")
            return {}
        
        sizes = [
            (320, 240, 'small'),
            (640, 480, 'medium'),
            (1024, 768, 'large'),
            (1920, 1080, 'xlarge')
        ]
        
        responsive_images = {}
        
        for width, height, size_name in sizes:
            try:
                with Image.open(image_path) as img:
                    # Convert to RGB if necessary
                    if img.mode in ('RGBA', 'LA', 'P'):
                        img = img.convert('RGB')
                    
                    # Resize maintaining aspect ratio
                    img.thumbnail((width, height), Image.Resampling.LANCZOS)
                    
                    # Create responsive image path
                    responsive_path = self._get_responsive_path(image_path, size_name)
                    
                    # Save responsive image
                    img.save(responsive_path, format='JPEG', quality=85, optimize=True)
                    
                    responsive_images[size_name] = responsive_path
                    logger.info(f"Responsive image created: {size_name} -> {responsive_path}")
                    
            except Exception as e:
                logger.error(f"Error creating responsive image {size_name}: {e}")
        
        return responsive_images
    
    def _get_optimized_path(self, original_path, quality, format):
        """Get path for optimized image"""
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        directory = os.path.dirname(original_path)
        return os.path.join(directory, f"{base_name}_{quality}.{format.lower()}")
    
    def _get_thumbnail_path(self, original_path, size):
        """Get path for thumbnail"""
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        directory = os.path.dirname(original_path)
        return os.path.join(directory, f"{base_name}_thumb_{size[0]}x{size[1]}.jpg")
    
    def _get_responsive_path(self, original_path, size_name):
        """Get path for responsive image"""
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        directory = os.path.dirname(original_path)
        return os.path.join(directory, f"{base_name}_{size_name}.jpg")

class StaticFileOptimizer:
    """
    Static file optimization utilities
    """
    
    def __init__(self):
        self.static_path = getattr(settings, 'STATIC_ROOT', 'static')
        self.media_path = getattr(settings, 'MEDIA_ROOT', 'media')
    
    def optimize_css(self, css_path):
        """Optimize CSS file"""
        try:
            with open(css_path, 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            # Basic CSS optimization
            optimized_css = self._optimize_css_content(css_content)
            
            # Create optimized file path
            optimized_path = self._get_optimized_file_path(css_path, 'css')
            
            # Write optimized CSS
            with open(optimized_path, 'w', encoding='utf-8') as f:
                f.write(optimized_css)
            
            logger.info(f"CSS optimized: {css_path} -> {optimized_path}")
            return optimized_path
            
        except Exception as e:
            logger.error(f"Error optimizing CSS {css_path}: {e}")
            return None
    
    def optimize_js(self, js_path):
        """Optimize JavaScript file"""
        try:
            with open(js_path, 'r', encoding='utf-8') as f:
                js_content = f.read()
            
            # Basic JS optimization
            optimized_js = self._optimize_js_content(js_content)
            
            # Create optimized file path
            optimized_path = self._get_optimized_file_path(js_path, 'js')
            
            # Write optimized JS
            with open(optimized_path, 'w', encoding='utf-8') as f:
                f.write(optimized_js)
            
            logger.info(f"JavaScript optimized: {js_path} -> {optimized_path}")
            return optimized_path
            
        except Exception as e:
            logger.error(f"Error optimizing JavaScript {js_path}: {e}")
            return None
    
    def _optimize_css_content(self, css_content):
        """Optimize CSS content"""
        # Remove comments
        css_content = self._remove_css_comments(css_content)
        
        # Remove unnecessary whitespace
        css_content = self._remove_unnecessary_whitespace(css_content)
        
        # Minify CSS
        css_content = self._minify_css(css_content)
        
        return css_content
    
    def _optimize_js_content(self, js_content):
        """Optimize JavaScript content"""
        # Remove comments
        js_content = self._remove_js_comments(js_content)
        
        # Remove unnecessary whitespace
        js_content = self._remove_unnecessary_whitespace(js_content)
        
        # Minify JS
        js_content = self._minify_js(js_content)
        
        return js_content
    
    def _remove_css_comments(self, css_content):
        """Remove CSS comments"""
        import re
        return re.sub(r'/\*.*?\*/', '', css_content, flags=re.DOTALL)
    
    def _remove_js_comments(self, js_content):
        """Remove JavaScript comments"""
        import re
        # Remove single-line comments
        js_content = re.sub(r'//.*$', '', js_content, flags=re.MULTILINE)
        # Remove multi-line comments
        js_content = re.sub(r'/\*.*?\*/', '', js_content, flags=re.DOTALL)
        return js_content
    
    def _remove_unnecessary_whitespace(self, content):
        """Remove unnecessary whitespace"""
        import re
        # Replace multiple spaces with single space
        content = re.sub(r'\s+', ' ', content)
        # Remove spaces around operators
        content = re.sub(r'\s*([{}:;,()])\s*', r'\1', content)
        return content.strip()
    
    def _minify_css(self, css_content):
        """Minify CSS content"""
        import re
        # Remove unnecessary semicolons
        css_content = re.sub(r';}', '}', css_content)
        # Remove spaces around colons
        css_content = re.sub(r'\s*:\s*', ':', css_content)
        # Remove spaces around commas
        css_content = re.sub(r'\s*,\s*', ',', css_content)
        return css_content
    
    def _minify_js(self, js_content):
        """Minify JavaScript content"""
        import re
        # Remove unnecessary semicolons
        js_content = re.sub(r';}', '}', js_content)
        # Remove spaces around operators
        js_content = re.sub(r'\s*([{}:;,()])\s*', r'\1', js_content)
        return js_content
    
    def _get_optimized_file_path(self, original_path, file_type):
        """Get path for optimized file"""
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        directory = os.path.dirname(original_path)
        return os.path.join(directory, f"{base_name}.min.{file_type}")

class CDNManager:
    """
    CDN management utilities
    """
    
    def __init__(self):
        self.cdn_url = getattr(settings, 'CDN_URL', '')
        self.static_url = getattr(settings, 'STATIC_URL', '/static/')
        self.media_url = getattr(settings, 'MEDIA_URL', '/media/')
    
    def get_cdn_url(self, file_path, file_type='static'):
        """Get CDN URL for file"""
        if not self.cdn_url:
            return file_path
        
        if file_type == 'static':
            return f"{self.cdn_url}{self.static_url}{file_path}"
        elif file_type == 'media':
            return f"{self.cdn_url}{self.media_url}{file_path}"
        else:
            return f"{self.cdn_url}/{file_path}"
    
    def generate_file_hash(self, file_path):
        """Generate hash for file for cache busting"""
        try:
            with open(file_path, 'rb') as f:
                file_content = f.read()
                return hashlib.md5(file_content).hexdigest()[:8]
        except Exception as e:
            logger.error(f"Error generating hash for {file_path}: {e}")
            return None
    
    def get_versioned_url(self, file_path, file_type='static'):
        """Get versioned URL for cache busting"""
        base_url = self.get_cdn_url(file_path, file_type)
        file_hash = self.generate_file_hash(file_path)
        
        if file_hash:
            # Add hash as query parameter
            separator = '&' if '?' in base_url else '?'
            return f"{base_url}{separator}v={file_hash}"
        
        return base_url

class StaticFileManager:
    """
    Static file management utilities
    """
    
    def __init__(self):
        self.image_optimizer = ImageOptimizer()
        self.file_optimizer = StaticFileOptimizer()
        self.cdn_manager = CDNManager()
    
    def optimize_uploaded_image(self, image_file, user_id, quality='medium'):
        """Optimize uploaded image"""
        try:
            # Create user-specific directory
            user_dir = os.path.join(self.image_optimizer.upload_path, 'images', str(user_id))
            os.makedirs(user_dir, exist_ok=True)
            
            # Save original image
            original_path = os.path.join(user_dir, image_file.name)
            with open(original_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)
            
            # Optimize image
            optimized_path = self.image_optimizer.optimize_image(
                original_path, 
                quality=quality,
                max_width=1920,
                max_height=1080
            )
            
            # Create thumbnail
            thumbnail_path = self.image_optimizer.create_thumbnail(
                original_path,
                size=(300, 300)
            )
            
            # Create responsive images
            responsive_images = self.image_optimizer.create_responsive_images(original_path)
            
            return {
                'original': original_path,
                'optimized': optimized_path,
                'thumbnail': thumbnail_path,
                'responsive': responsive_images
            }
            
        except Exception as e:
            logger.error(f"Error optimizing uploaded image: {e}")
            return None
    
    def get_optimized_image_urls(self, image_path):
        """Get optimized image URLs for different sizes"""
        try:
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            directory = os.path.dirname(image_path)
            
            urls = {}
            
            # Original image
            urls['original'] = self.cdn_manager.get_cdn_url(image_path, 'media')
            
            # Optimized image
            optimized_path = os.path.join(directory, f"{base_name}_medium.jpg")
            if os.path.exists(optimized_path):
                urls['optimized'] = self.cdn_manager.get_cdn_url(optimized_path, 'media')
            
            # Thumbnail
            thumbnail_path = os.path.join(directory, f"{base_name}_thumb_300x300.jpg")
            if os.path.exists(thumbnail_path):
                urls['thumbnail'] = self.cdn_manager.get_cdn_url(thumbnail_path, 'media')
            
            # Responsive images
            sizes = ['small', 'medium', 'large', 'xlarge']
            for size in sizes:
                responsive_path = os.path.join(directory, f"{base_name}_{size}.jpg")
                if os.path.exists(responsive_path):
                    urls[size] = self.cdn_manager.get_cdn_url(responsive_path, 'media')
            
            return urls
            
        except Exception as e:
            logger.error(f"Error getting optimized image URLs: {e}")
            return {}
    
    def optimize_static_files(self):
        """Optimize all static files"""
        try:
            # Find CSS files
            css_files = self._find_files(self.static_path, '.css')
            for css_file in css_files:
                self.file_optimizer.optimize_css(css_file)
            
            # Find JS files
            js_files = self._find_files(self.static_path, '.js')
            for js_file in js_files:
                self.file_optimizer.optimize_js(js_file)
            
            logger.info("Static files optimization completed")
            
        except Exception as e:
            logger.error(f"Error optimizing static files: {e}")
    
    def _find_files(self, directory, extension):
        """Find files with specific extension"""
        files = []
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith(extension):
                    files.append(os.path.join(root, filename))
        return files

# Global instances
image_optimizer = ImageOptimizer()
file_optimizer = StaticFileOptimizer()
cdn_manager = CDNManager()
static_manager = StaticFileManager()
