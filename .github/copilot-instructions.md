# GitHub Copilot Instructions

## General Coding Guidelines
1. Python always assumes version 3.12.
2. Always use type hints in function signatures and class definitions.
3. Always use Google-style docstrings for functions, methods, and classes.
4. A class's docstring should be included with the `__init__` method, not the class name.
5. Parameters in docstrings should not include the type (the type is already provided in the type hints).

## Copilot-Specific Instructions
1. When generating code, ensure it adheres to the above coding guidelines.
2. When modifying existing code, ensure consistency with the repository's coding style.
3. When generating new files, include a brief header comment explaining the file's purpose.
4. Always prioritize readability and maintainability in code suggestions.
5. Avoid introducing unnecessary dependencies unless explicitly requested.

## Example of a Function Docstring
```python
def example_function(param1: int, param2: str) -> bool:
    """
    Performs an example operation.

    Args:
        param1: The first parameter.
        param2: The second parameter.

    Returns:
        A boolean indicating the result of the operation.
    """
    return True
```

## Example of a Class Docstring
```python
class ExampleClass:
    def __init__(self, name: str, age: int) -> None:
        """
        Initializes the ExampleClass.

        Args:
            name: The name of the person.
            age: The age of the person.
        """
        self.name = name
        self.age = age
```