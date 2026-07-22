from main import execution_plan


def test_execution_plan_is_short_and_readable():
    assert execution_plan("создай index.html") == [
        "Изучить нужные файлы",
        "Внести запрошенные изменения",
        "Проверить результат",
    ]
    assert "Проверить" in execution_plan("проверь проект")[1]
