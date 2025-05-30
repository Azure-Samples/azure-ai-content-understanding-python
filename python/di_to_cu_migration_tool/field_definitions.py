class FieldDefinitions:
    def __init__(self):
        self._definitions = {}

    def add_definition(self, key: str, value: dict) -> None:
        """
        Add a new field definition.

        Args:
            key (str): The key for the field definition.
            value (dict): The value for the field definition.
        """
        self._definitions[key] = value

    def get_definition(self, key: str) -> dict:
        """
        Retrieve a field definition by key.

        Args:
            key (str): The key for the field definition.

        Returns:
            dict: The field definition, or None if the key does not exist.
        """
        return self._definitions.get(key)

    def clear_definitions(self) -> None:
        """
        Clear all field definitions.
        """
        self._definitions.clear()

    def get_all_definitions(self) -> dict:
        """
        Retrieve all field definitions.

        Returns:
            dict: All field definitions.
        """
        return self._definitions
