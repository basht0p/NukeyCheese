import os
import uuid
import random
import yaml
from PIL import Image
from collections import deque

def load_config(config_path="config.yml"):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

def load_words(words_path="words.txt"):
    """Load words from a text file."""
    with open(words_path, 'r') as file:
        words = [line.strip() for line in file if line.strip()]
    return words

def generate_directory_name(words, depth, index):
    """Generate a directory name using 1-3 random words from the word list."""
    num_words = random.randint(1, 3)
    selected_words = random.sample(words, min(num_words, len(words)))
    name = "_".join(selected_words)
    return f"{name}_{depth}_{index}"

def get_directory_size(directory):
    """Calculate the total size of a directory and all its contents in bytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size

# Load configuration
config = load_config()
words = load_words()
max_leaves_per_branch = config['max_leaf_per_branch']
depth = config['max_branch_depth']
root_directory = config['root_directory']
orig_path = config['src_image_path']
target_bytes = config['target_bytes']
minimum_images_per_directory = config['minimum_images_per_directory']
max_path_length = config['max_path_length']
max_directories = config['max_directories']

# Load your source image
if not os.path.exists(orig_path):
    raise FileNotFoundError(f"Cannot find '{orig_path}' in the current directory.")

orig = Image.open(orig_path)
width, height = orig.size
mode = orig.mode  # e.g. "RGB", "RGBA" or "L"

def save_one_pixel_variant(image, mode, width, height, save_directory, estimated_file_size):
    """Save a variant of the image with one random pixel changed."""
    img = image.copy()

    # Pick one random pixel
    x = random.randint(0, width - 1)
    y = random.randint(0, height - 1)

    # Generate a random color consistent with the image mode
    if mode == "RGB":
        color = (random.randint(0, 255),
                 random.randint(0, 255),
                 random.randint(0, 255))
    elif mode == "RGBA":
        color = (random.randint(0, 255),
                 random.randint(0, 255),
                 random.randint(0, 255),
                 random.randint(0, 255))
    elif mode == "L":  # grayscale
        color = random.randint(0, 255)
    else:
        raise ValueError(f"Unsupported image mode: {mode}")

    # Apply the one‐pixel edit
    img.putpixel((x, y), color)

    # Save under a new GUID name in the specified directory as BMP for speed
    new_filename = f"{uuid.uuid4().hex[:8]}.bmp"
    save_path = os.path.join(save_directory, new_filename)
    img.save(save_path, "BMP")

    # Use estimated size to avoid disk I/O - only get actual size occasionally
    return save_path, estimated_file_size

def generate_batch_variants(image, mode, width, height, save_directory, estimated_file_size, batch_size):
    """Generate multiple image variants in a batch for better performance."""
    saved_files = []
    
    # Pre-generate all random modifications
    modifications = []
    for _ in range(batch_size):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        
        if mode == "RGB":
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        elif mode == "RGBA":
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        elif mode == "L":
            color = random.randint(0, 255)
        else:
            raise ValueError(f"Unsupported image mode: {mode}")
            
        modifications.append((x, y, color))
    
    # Pre-generate all filenames
    filenames = [f"{uuid.uuid4().hex[:8]}.bmp" for _ in range(batch_size)]
    
    # Create and save all variants
    for i, ((x, y, color), filename) in enumerate(zip(modifications, filenames)):
        img = image.copy()
        img.putpixel((x, y), color)
        
        save_path = os.path.join(save_directory, filename)
        img.save(save_path, "BMP")
        saved_files.append((save_path, estimated_file_size))
    
    return saved_files

def generate_tree_with_images(root_path, max_depth, max_leaf_per_branch, target_size, min_images_per_dir, words_list, max_dirs):
    """
    Creates a random directory tree and fills it with image variants 
    until the total size approaches the target size without exceeding it.
    Ensures each directory has at least min_images_per_dir images.
    Optimized for maximum performance - path length checking removed.
    """
    # Creates the root directory if it doesn't exist
    os.makedirs(root_path, exist_ok=True)

    # Get estimated file size from original image (BMP will be larger than source)
    estimated_file_size = os.path.getsize(orig_path) * 3  # BMP is typically 3x larger
    
    # Create initial directory structure
    all_directories = [root_path]
    queue = deque([(root_path, 0)])
    directories_created = 1  # Count the root directory

    # Build the directory tree first (simplified - no path length checks)
    while queue and directories_created < max_dirs:
        current_path, current_depth = queue.popleft()

        if current_depth < max_depth:
            # Determine the number of child directories
            num_children = random.randint(1, max_leaf_per_branch)
            
            for i in range(num_children):
                # Check if we've hit the directory limit
                if directories_created >= max_dirs:
                    break
                
                # Create directory name using words (simplified)
                dir_name = generate_directory_name(words_list, current_depth, i)
                new_dir_path = os.path.join(current_path, dir_name)
                
                try:
                    os.makedirs(new_dir_path, exist_ok=True)
                    all_directories.append(new_dir_path)
                    queue.append((new_dir_path, current_depth + 1))
                    directories_created += 1
                except OSError as e:
                    print(f"Error creating directory {new_dir_path}: {e}")

    print(f"Created {len(all_directories)} directories")
    if directories_created >= max_dirs:
        print(f"Reached maximum directory limit of {max_dirs} - continuing with image creation")
    
    # Use all directories (no path length filtering)
    safe_directories = all_directories
    
    print(f"Directories for file creation: {len(safe_directories)}")
    
    # Track size without expensive directory scans
    current_size = 0
    images_created = 0
    directory_image_counts = {dir_path: 0 for dir_path in safe_directories}
    
    # Pre-calculate how many images we need total for minimum requirements
    total_minimum_images = len(safe_directories) * min_images_per_dir
    minimum_size_needed = total_minimum_images * estimated_file_size
    
    print(f"Ensuring each directory has at least {min_images_per_dir} images...")
    print(f"Estimated minimum size needed: {minimum_size_needed} bytes")
    
    # Fill each directory with minimum required images (batch approach)
    batch_size = 20  # Process 20 images at a time for better performance
    for target_dir in safe_directories:
        remaining_for_dir = min_images_per_dir
        
        while remaining_for_dir > 0 and current_size < target_size:
            # Determine batch size for this iteration
            current_batch_size = min(batch_size, remaining_for_dir, 
                                   max(1, (target_size - current_size) // estimated_file_size))
            
            try:
                batch_results = generate_batch_variants(orig, mode, width, height, target_dir, 
                                                      estimated_file_size, current_batch_size)
                
                for save_path, file_size in batch_results:
                    current_size += file_size
                    images_created += 1
                    directory_image_counts[target_dir] += 1
                    remaining_for_dir -= 1
                    
                    if current_size >= target_size:
                        break
                        
            except Exception as e:
                print(f"Error creating image batch in {target_dir}: {e}")
                break
        
        if current_size >= target_size:
            break
    
    print(f"Minimum images phase complete. Current size: {current_size} bytes, Images: {images_created}")
    
    # Pre-select random directories for remaining images to avoid repeated random.choice calls
    remaining_size_needed = target_size - current_size
    estimated_remaining_images = max(0, remaining_size_needed // estimated_file_size)
    
    if estimated_remaining_images > 0:
        # Pre-generate random directory choices for better performance
        random_dirs = [random.choice(safe_directories) for _ in range(min(estimated_remaining_images + 10, 1000))]
        dir_index = 0
        
        # Continue filling directories until we reach target size (using batches)
        while current_size < target_size and dir_index < len(random_dirs):
            target_dir = random_dirs[dir_index]
            
            # Calculate how many images we can fit in this batch
            remaining_capacity = (target_size - current_size) // estimated_file_size
            current_batch_size = min(batch_size, remaining_capacity, len(random_dirs) - dir_index)
            
            if current_batch_size <= 0:
                break
                
            try:
                batch_results = generate_batch_variants(orig, mode, width, height, target_dir, 
                                                      estimated_file_size, current_batch_size)
                
                for save_path, file_size in batch_results:
                    current_size += file_size
                    images_created += 1
                    directory_image_counts[target_dir] += 1
                    
                    # Check if adding another image would exceed the target (use estimation)
                    if current_size + estimated_file_size > target_size:
                        print(f"Stopping to avoid exceeding target size. Current size: {current_size} bytes")
                        break
                        
                # Progress update every 200 images (batch adjusted)
                if images_created % 200 == 0:
                    print(f"Progress: {images_created} images created, {current_size}/{target_size} bytes ({current_size/target_size*100:.1f}%)")
                
                dir_index += 1
                    
            except Exception as e:
                print(f"Error creating image batch: {e}")
                break
    
    # Get final accurate size only once at the end
    final_size = get_directory_size(root_path)
    
    # Calculate statistics
    min_images_in_dir = min(directory_image_counts.values()) if directory_image_counts else 0
    max_images_in_dir = max(directory_image_counts.values()) if directory_image_counts else 0
    avg_images_in_dir = sum(directory_image_counts.values()) / len(directory_image_counts) if directory_image_counts else 0
    
    print(f"\nTree generation complete!")
    print(f"Total directories created: {len(all_directories)}")
    print(f"Total images created: {images_created}")
    print(f"Images per directory - Min: {min_images_in_dir}, Max: {max_images_in_dir}, Avg: {avg_images_in_dir:.1f}")
    print(f"Estimated size: {current_size} bytes")
    print(f"Final size: {final_size} bytes")
    print(f"Target size: {target_size} bytes")
    print(f"Efficiency: {final_size/target_size*100:.1f}%")
    print(f"Max directories limit: {max_dirs} (reached: {'Yes' if directories_created >= max_dirs else 'No'})")

if __name__ == "__main__":
    print(f"Starting tree generation with target size: {target_bytes} bytes")
    print(f"Source image: {orig_path}")
    print(f"Root directory: {root_directory}")
    print(f"Max depth: {depth}, Max leaves per branch: {max_leaves_per_branch}")
    print(f"Minimum images per directory: {minimum_images_per_directory}")
    print(f"Max directories limit: {max_directories}")
    print(f"Loaded {len(words)} words for directory naming")
    print(f"Using BMP format for maximum speed")
    
    generate_tree_with_images(root_directory, depth, max_leaves_per_branch, target_bytes, minimum_images_per_directory, words, max_directories)
