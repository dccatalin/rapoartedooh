import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"sys.path: {sys.path}")

try:
    import PIL
    print(f"PIL path: {PIL.__file__}")
    print(f"PIL version: {PIL.__version__}")
    from PIL import Image
    print("Successfully imported Image from PIL")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
