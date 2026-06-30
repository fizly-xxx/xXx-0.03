import os

def collect_code_to_txt(source_dir, output_file, allowed_dirs, allowed_extensions):
    current_script_name = os.path.basename(__file__)

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk(source_dir):
            
            # Якщо ми знаходимося в головній папці, обрізаємо список папок для пошуку
            # Залишаємо ТІЛЬКИ ті, що є в allowed_dirs
            if root == source_dir:
                dirs[:] = [d for d in dirs if d in allowed_dirs]
            
            for file in files:
                # Пропускаємо сам скрипт та вихідний файл
                if file == current_script_name or file == output_file:
                    continue

                # Перевіряємо розширення файлу
                if any(file.endswith(ext) for ext in allowed_extensions):
                    file_path = os.path.join(root, file)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()
                            
                            outfile.write(f"\n\n/* {'='*42}\n")
                            outfile.write(f"Файл: {file_path}\n")
                            outfile.write(f"{'='*42} */\n\n")
                            
                            outfile.write(content)
                    except Exception as e:
                        print(f"Не вдалося прочитати {file_path}: {e}")

# === Налаштування ===
source_directory = "."  
output_filename = "all_code_project.txt" 

# ПАПКИ, ЯКІ ТРЕБА СКАНУВАТИ (впиши сюди тільки свої папки з кодом)
allowed_folders = {"services", "controllers", "interfaces", "ui"} 

allowed_exts = {".py", ".js", ".html", ".css", ".md", ".pyw"}

# Запуск
collect_code_to_txt(source_directory, output_filename, allowed_folders, allowed_exts)
print(f"Готово! Код тільки з вибраних папок збережено у: {output_filename}")