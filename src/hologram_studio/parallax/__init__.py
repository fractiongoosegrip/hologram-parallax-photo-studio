"""Depth -> displacement, layer slicing, focal-plane selection."""
from hologram_studio.parallax.layer_slicer import slice_layers, ParallaxLayer
from hologram_studio.parallax.displacement import displacement_field

__all__ = ["slice_layers", "ParallaxLayer", "displacement_field"]