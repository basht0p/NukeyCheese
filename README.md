# Nukey Cheese 🧀💣  
*A thermonuclear rodent for your disks.*

Nukey Cheese is a file system obliteration tool disguised as a family-friendly Chuck E. Cheese photo dump. It recursively fills a target drive with randomly generated directory trees and copies of an animatronic hellspawn (`image.bmp`) until a specified byte quota is reached.

Use it to "sanitize" disks in a way that ensures two things:
1. Previous data is gone.
2. Nobody will *ever* want to recover what replaced it.

---

## 🔧 Configuration

Nukey Cheese behavior is controlled via a simple config structure:

```yaml
max_leaf_per_branch: 5                # Max subdirectories per directory
max_branch_depth: 4                   # Max recursion depth
root_directory: 'X:\\'                # Target root to begin infestation
src_image_path: 'image.bmp'           # The sacred JPEG/BMP/PNG of Chuck E. Cheese
target_bytes: 100000000000            # Target total size (e.g., 100GB)
minimum_images_per_directory: 10      # Guarantees image spam even in shallow branches
max_path_length: 250                  # Ensures Windows doesn't have a meltdown
max_directories: 100                  # Safety valve for total directory count
