import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RouteContractTest(unittest.TestCase):
    # Asegura que los endpoints conservan ruta, método y parámetros.
    def test_http_routes_preserved(self):
        contract = json.loads((ROOT / 'tests/route_contract.json').read_text())
        total = 0
        for module, expected in contract.items():
            file = ROOT / 'app/presentation/api/routers' / (module + '.py')
            tree = ast.parse(file.read_text())
            actual = []
            for node in tree.body:
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for dec in node.decorator_list:
                    if (isinstance(dec, ast.Call)
                            and isinstance(dec.func, ast.Attribute)
                            and getattr(dec.func.value, 'id', None) == 'router'):
                        actual.append({
                            'name': node.name,
                            'method': dec.func.attr.upper(),
                            'path': ast.literal_eval(dec.args[0]),
                            'params': [arg.arg for arg in node.args.args],
                        })
            self.assertEqual(actual, expected, module)
            total += len(actual)
        self.assertEqual(total, 73)
