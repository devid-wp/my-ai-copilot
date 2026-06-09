# core/diff_applier.py
def apply_diff(file_path, response):
    # Упрощенная логика: перезапись файла ответом ИИ
    # В идеале здесь должен быть парсинг блоков SEARCH/REPLACE
    with open(file_path, "w") as f:
        f.write(response)