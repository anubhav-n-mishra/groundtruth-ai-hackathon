"""
QR Code Generation Module.

This module generates QR codes that link to dashboard sessions,
allowing users to access live data by scanning the QR code on
the final slide of the PowerPoint report.
"""

import io
import os
from pathlib import Path
from typing import Optional
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from qrcode.image.styles.colormasks import SolidFillColorMask
from PIL import Image

from core.logger import get_logger

logger = get_logger("qrcode_gen")


def generate_dashboard_url(
    base_url: str,
    session_id: str,
    token: str
) -> str:
    """
    Generate the full dashboard URL with session and token.
    
    Args:
        base_url: The base URL of the application (e.g., http://localhost:8000)
        session_id: Unique session identifier for this report
        token: Access token for authentication
        
    Returns:
        Full dashboard URL with embedded token
    """
    return f"{base_url}/dashboard/{session_id}?token={token}"


def generate_qr_code(
    url: str,
    output_path: Optional[str] = None,
    size: int = 300,
    border: int = 2,
    fill_color: str = "#1a1a2e",
    back_color: str = "#ffffff",
    logo_path: Optional[str] = None
) -> bytes:
    """
    Generate a QR code image for the given URL.
    
    Args:
        url: The URL to encode in the QR code
        output_path: Optional path to save the QR code image
        size: Size of the QR code in pixels (width and height)
        border: Border size around the QR code
        fill_color: Color of the QR code modules (dark parts)
        back_color: Background color of the QR code
        logo_path: Optional path to a logo to embed in the center
        
    Returns:
        QR code image as bytes (PNG format)
    """
    logger.info(f"Generating QR code for URL: {url[:50]}...")
    
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,  # Auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # High error correction for logo
        box_size=10,
        border=border,
    )
    
    # Add data
    qr.add_data(url)
    qr.make(fit=True)
    
    # Create styled image
    try:
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=RoundedModuleDrawer(),
            color_mask=SolidFillColorMask(
                back_color=_hex_to_rgb(back_color),
                front_color=_hex_to_rgb(fill_color)
            )
        )
    except Exception as e:
        logger.warning(f"Styled QR failed, using basic: {e}")
        # Fallback to basic QR code
        img = qr.make_image(fill_color=fill_color, back_color=back_color)
    
    # Convert to PIL Image if needed
    if not isinstance(img, Image.Image):
        img = img.get_image()
    
    # Resize to desired size
    img = img.resize((size, size), Image.Resampling.LANCZOS)
    
    # Add logo if provided
    if logo_path and os.path.exists(logo_path):
        img = _add_logo_to_qr(img, logo_path)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    # Optionally save to file
    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(img_bytes.getvalue())
        logger.info(f"QR code saved to: {output_path}")
    
    logger.info("QR code generated successfully")
    return img_bytes.getvalue()


def generate_qr_for_dashboard(
    base_url: str,
    session_id: str,
    token: str,
    output_path: Optional[str] = None,
    size: int = 300
) -> tuple[bytes, str]:
    """
    Generate a QR code for dashboard access.
    
    This is a convenience function that combines URL generation
    and QR code creation.
    
    Args:
        base_url: The base URL of the application
        session_id: Unique session identifier
        token: Access token for authentication
        output_path: Optional path to save the QR code
        size: Size of the QR code in pixels
        
    Returns:
        Tuple of (QR code bytes, full dashboard URL)
    """
    # Generate the dashboard URL
    dashboard_url = generate_dashboard_url(base_url, session_id, token)
    
    # Generate QR code
    qr_bytes = generate_qr_code(
        url=dashboard_url,
        output_path=output_path,
        size=size
    )
    
    return qr_bytes, dashboard_url


def _hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _add_logo_to_qr(qr_img: Image.Image, logo_path: str) -> Image.Image:
    """
    Add a logo to the center of the QR code.
    
    Args:
        qr_img: The QR code image
        logo_path: Path to the logo file
        
    Returns:
        QR code image with logo embedded
    """
    try:
        logo = Image.open(logo_path)
        
        # Calculate logo size (max 25% of QR code)
        qr_width, qr_height = qr_img.size
        logo_max_size = min(qr_width, qr_height) // 4
        
        # Resize logo maintaining aspect ratio
        logo.thumbnail((logo_max_size, logo_max_size), Image.Resampling.LANCZOS)
        
        # Calculate position to center logo
        logo_pos = (
            (qr_width - logo.width) // 2,
            (qr_height - logo.height) // 2
        )
        
        # Create a copy of QR code
        qr_with_logo = qr_img.copy()
        
        # Paste logo (handle transparency if present)
        if logo.mode == 'RGBA':
            qr_with_logo.paste(logo, logo_pos, logo)
        else:
            qr_with_logo.paste(logo, logo_pos)
        
        return qr_with_logo
        
    except Exception as e:
        logger.warning(f"Failed to add logo: {e}")
        return qr_img


# Test function
def test_qr_generation():
    """Test QR code generation."""
    print("Testing QR code generation...")
    
    # Test data
    test_url = "http://localhost:8000/dashboard/abc123def456?token=test_token_xyz"
    
    # Generate QR code
    qr_bytes = generate_qr_code(
        url=test_url,
        output_path="tmp/test_qr.png",
        size=300
    )
    
    print(f"QR code generated: {len(qr_bytes)} bytes")
    print("Saved to: tmp/test_qr.png")
    
    # Test with dashboard helper
    qr_bytes2, dashboard_url = generate_qr_for_dashboard(
        base_url="http://localhost:8000",
        session_id="session_123",
        token="secure_token_abc",
        output_path="tmp/test_dashboard_qr.png"
    )
    
    print(f"Dashboard URL: {dashboard_url}")
    print(f"QR code size: {len(qr_bytes2)} bytes")
    print("Test complete!")


if __name__ == "__main__":
    test_qr_generation()
