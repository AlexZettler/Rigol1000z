from os import system as execute_cmd


def title_message(title_str: str, title_size: int):
    print(
        f"{'*' * title_size}\n"
        f"* {title_str.center(title_size - 4, ' ')} *\n"
        f"{'*' * title_size}"
    )


if __name__ == '__main__':
    str_width = 24

    title_message('Starting type checking', str_width)
    execute_cmd('mypy -p Rigol1000z')
    title_message('Type checking Complete', str_width)
    print("\n")

    title_message('Starting tests', str_width)
    execute_cmd('pipenv run python -m unittest discover -s ./tests')
    title_message('Testing complete', str_width)
    print("\n")

    title_message('Generating documentation', str_width)
    execute_cmd('pdoc Rigol1000z --html --force')
    title_message('Documentation generating complete', str_width)
    print("\n")
