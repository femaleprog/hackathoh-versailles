import os


def load_prompts(filenames):
    prompts_dict = {}
    for filename in filenames:
        try:
            with open(filename, "r", encoding="utf-8") as file:
                key = os.path.basename(filename).replace(".txt", "")
                prompts_dict[key] = file.read()
        except FileNotFoundError:
            print(f"Error: The file '{filename}' was not found.")
            return {}
        except Exception as e:
            print(f"An error occurred while reading '{filename}': {e}")
            return {}
    return prompts_dict
