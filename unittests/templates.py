import unittest
import sys
import os
import logging

# Добавляем текущую директорию в sys.path для импорта
sys.path.append(os.getcwd())

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(message)s")

class TestLordTemplate(unittest.TestCase):
    def setUp(self):
        """Подготовка перед каждым тестом"""
        from bot.misc.utils.templates import LordTemplate
        self.lord_template = LordTemplate()

    def log_result(self, result, expected):
        """Логирует результаты теста"""
        print()
        logging.info(f"Result: {result}")
        logging.info(f"Expected: {expected}")

    def test_basic_substitution(self):
        """Тест базовой подстановки переменной"""
        template = "{name}"
        data = {"name": "Alice"}
        result = self.lord_template.render(template, data)
        self.log_result(result, "Alice")
        self.assertEqual(result, "Alice")

    def test_missing_variable_with_default(self):
        """Тест на отсутствие переменной с дефолтным значением"""
        template = "{name | 'Guest'}"
        data = {}
        result = self.lord_template.render(template, data)
        self.log_result(result, "Guest")
        self.assertEqual(result, "Guest")

    def test_variable_with_flag_upper(self):
        """Тест с флагом upper"""
        template = "{name?&upper}"
        data = {"name": "alice"}
        result = self.lord_template.render(template, data)
        self.log_result(result, "ALICE")
        self.assertEqual(result, "ALICE")

    def test_variable_with_flag_and_default(self):
        """Тест с флагом и дефолтным значением"""
        template = "{name?&upper | 'Guest'}"
        data = {}
        result = self.lord_template.render(template, data)
        self.log_result(result, "Guest")
        self.assertEqual(result, "Guest")

    def test_variable_nested_key(self):
        """Тест с вложенным ключом"""
        template = "{user.name}"
        data = {"user": {"name": "Bob"}}
        result = self.lord_template.render(template, data)
        self.log_result(result, "Bob")
        self.assertEqual(result, "Bob")

    def test_variable_nested_key_with_default(self):
        """Тест с вложенным ключом и дефолтным значением"""
        template = "{user.name | 'NoName'}"
        data = {}
        result = self.lord_template.render(template, data)
        self.log_result(result, "NoName")
        self.assertEqual(result, "NoName")

    def test_variable_nested_key_with_default_empry_field(self):
        """Тест с вложенным ключом и дефолтным значением"""
        template = "{user.name | 'NoName'}"
        data = {'user.name': ''}
        result = self.lord_template.render(template, data)
        self.log_result(result, "NoName")
        self.assertEqual(result, "NoName")
        
        
    def test_variable_nested_key_empry_field(self):
        """Тест с вложенным ключом и дефолтным значением"""
        template = "{user.name}"
        data = {'user.name': ''}
        result = self.lord_template.render(template, data)
        self.log_result(result, "")
        self.assertEqual(result, "")

    def test_variable_nested_key_with_flag(self):
        """Тест с вложенным ключом и флагом"""
        template = "{user.name?&upper}"
        data = {"user": {"name": "bob"}}
        result = self.lord_template.render(template, data)
        self.log_result(result, "BOB")
        self.assertEqual(result, "BOB")

    def test_json_structure_no_match(self):
        """Тест для структуры JSON с неподходящими значениями"""
        template = '''
        {
            "content": null,
            "embeds": [
                {
                    "description": "{user.name | 'Guest'}",
                    "color": 12345
                },
                {
                    "description": "{not_existing_key | 'Fallback'}"
                }
            ]
        }
        '''
        data = {"user": {"name": "Charlie"}}
        result = self.lord_template.render(template, data)
        self.log_result(result, "Expected output with 'Charlie' and 'Fallback'")
        self.assertIn('"description": "Charlie"', result)
        self.assertIn('"description": "Fallback"', result)

    def test_multiple_variables(self):
        """Тест с несколькими переменными"""
        template = "{{first_name} {last_name}}"
        data = {"first_name": "John", "last_name": "Doe"}
        result = self.lord_template.render(template, data)
        self.log_result(result, "{John Doe}")
        self.assertEqual(result, "{John Doe}")

    def test_variable_with_multiple_flags(self):
        """Тест с несколькими флагами"""
        template = "{name?&upper?&quote}"
        data = {"name": 'alice "the best"'}
        result = self.lord_template.render(template, data)
        self.log_result(result, 'ALICE \\"THE BEST\\"')
        self.assertEqual(result, 'ALICE \\"THE BEST\\"')

    def test_variable_with_json_like_structure(self):
        """Тест с обманкой в виде статичного JSON"""
        template = '{\"name\": \"Guest\"}'
        data = {}
        result = self.lord_template.render(template, data)
        self.log_result(result, "{\"name\": \"Guest\"}")
        self.assertEqual(result, "{\"name\": \"Guest\"}")  # Ожидаем, что строка не изменится

if __name__ == "__main__":
    unittest.main(verbosity=2)
