import ast
import unittest
from pathlib import Path
from app.infrastructure.database.queries.catalog import QUERIES


ROOT = Path(__file__).resolve().parents[1]


class QueryCatalogTest(unittest.TestCase):
    # Comprueba que todos los identificadores referidos estÃ¡n registrados.
    def test_all_query_keys_registered(self):
        catalog = QUERIES
        self.assertGreaterEqual(len(catalog), 115)
        references = set()
        usecases = ROOT / "app/application/use_cases"
        for file in usecases.rglob("*.py"):
            tree = ast.parse(file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                if (isinstance(node.func, ast.Attribute)
                        and node.func.attr == "execute"
                        and isinstance(node.args[0], ast.Constant)):
                    references.add(node.args[0].value)
                if (isinstance(node.func, ast.Name)
                        and node.func.id == "QueryRef"
                        and isinstance(node.args[0], ast.Constant)):
                    references.add(node.args[0].value)
        self.assertTrue(references)
        self.assertFalse(references - set(catalog))

    # Garantiza que los casos de uso no importan adaptadores concretos.
    def test_dependency_direction(self):
        for path in (ROOT / "app/application/use_cases").rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertNotIn("from app.infrastructure", source)
            self.assertNotIn("from fastapi", source)
            self.assertNotIn("from psycopg", source)


if __name__ == "__main__":
    unittest.main()
