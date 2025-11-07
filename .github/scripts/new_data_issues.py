import os
import re

def save_data_file(title, content):
    if "[NEW-PREDICTION]" in title:
        base_directory = "data/posts"
    elif "[NEW-AUTHOR]" in title:
        base_directory = "data/authors"
    else:
        raise ValueError("Title format error")

    max_number = 0
    for subdir in os.listdir(base_directory):
        if subdir.endswith('000') and subdir.isdigit():
            dir_path = os.path.join(base_directory, subdir)
            for filename in os.listdir(dir_path):
                if filename.endswith('.md'):
                    match = re.match(r'^(\d+)\.md$', filename)
                    if match:
                        max_number = max(max_number, int(match.group(1)))

    new_number = max_number + 1
    
    target_dir = str((new_number // 1000 + 1) * 1000)
    full_target_path = os.path.join(base_directory, target_dir)
    
    os.makedirs(full_target_path, exist_ok=True)
    
    new_filename = f"{new_number}.md"
    new_file_path = os.path.join(full_target_path, new_filename)
    
    with open(new_file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
#
issue_title = os.environ.get('ISSUE_TITLE', '')
issue_body = os.environ.get('ISSUE_BODY', '')

save_data_file(issue_title, issue_body)

