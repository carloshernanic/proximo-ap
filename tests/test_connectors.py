"""Offline tests: parsers run against small synthetic pages, never the network."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import grupozap  # noqa: E402
from http_util import apply_client_filters, slugify  # noqa: E402


def load_cli(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ".agents" / "skills" / name / "cli.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


quintoandar = load_cli("quintoandar-search")


def search_args(**overrides):
    base = dict(
        cidade="São Paulo", uf="SP", bairro=None, zona=None, negocio="aluguel",
        tipo="apartamento", quartos=None, banheiros=None, vagas=None, area_min=None,
        area_max=None, preco_min=None, preco_max=None, total_max=None, pets=None,
        mobiliado=None, paginas=1, limit=60,
    )
    base.update(overrides)
    return Namespace(**base)


ZAP_PAGE = """<html><script type="application/ld+json">{"@type": "ItemList",
"description": "1.234 anúncios de Apartamentos para alugar",
"itemListElement": [{"item": {"@type": "Product", "@id": "111",
 "name": "Apartamento para alugar com 65 m², 2 quartos, 2 banheiros, 1 vaga em  Pinheiros, São Paulo",
 "url": "https://www.zapimoveis.com.br/imovel/a-id-111/", "additionalType": "https://schema.org/Apartment",
 "address": {"streetAddress": "Rua dos Pinheiros", "addressLocality": "São Paulo"},
 "numberOfBedrooms": 2, "numberOfBathroomsTotal": 2, "floorSize": {"value": 65},
 "amenityFeature": [{"value": "Furnished"}, {"value": "Pool"}], "petsAllowed": true,
 "offers": {"price": 3000, "additionalProperty": {"name": "Condominium Fee", "value": 518}}}},
 {"item": {"@type": "Product", "@id": "222",
 "name": "Apartamento para alugar com 30 m², 1 quarto, 1 banheiro em  Centro, São Paulo",
 "url": "https://www.zapimoveis.com.br/imovel/b-id-222/",
 "numberOfBedrooms": 1, "floorSize": {"value": 30}, "petsAllowed": false,
 "offers": {"price": 1500}}}]}</script></html>"""


class GrupoZapTests(unittest.TestCase):
    def test_parses_listing_fields(self):
        results, total = grupozap.parse_search_page(ZAP_PAGE, "zap", "aluguel")
        self.assertEqual(total, 1234)
        first = results[0]
        self.assertEqual(first["id"], "zap-111")
        self.assertEqual((first["aluguel"], first["condominio"], first["total"]), (3000, 518, 3518))
        self.assertEqual((first["quartos"], first["vagas"], first["area_m2"]), (2, 1, 65))
        self.assertEqual(first["bairro"], "Pinheiros")
        self.assertTrue(first["mobiliado"])
        self.assertIn("piscina", first["comodidades"])
        self.assertEqual(results[1]["vagas"], 0)  # no "vaga" in the title
        self.assertIsNone(results[1]["condominio"])

    def test_zap_url_with_and_without_zone(self):
        url = grupozap.build_search_url("zap", search_args(bairro="Pinheiros", zona="zona-oeste", quartos=2, preco_max=4000), 2)
        self.assertEqual(url, "https://www.zapimoveis.com.br/aluguel/apartamentos/sp+sao-paulo+zona-oeste+pinheiros/?quartos=2&precoMaximo=4000&pagina=2")
        url = grupozap.build_search_url("zap", search_args(cidade="Campinas", bairro="Cambuí"), 1)
        self.assertEqual(url, "https://www.zapimoveis.com.br/aluguel/apartamentos/sp+campinas++cambui/")
        url = grupozap.build_search_url("zap", search_args(bairro="Vila Olímpia", zona="zona-sul", negocio="venda"), 1)
        self.assertEqual(url, "https://www.zapimoveis.com.br/venda/apartamentos/sp+sao-paulo+zona-sul+vl-olimpia/")

    def test_vivareal_url(self):
        url = grupozap.build_search_url("vivareal", search_args(bairro="Vila Mariana", zona="zona-sul", negocio="venda", tipo="casa"), 1)
        self.assertEqual(url, "https://www.vivareal.com.br/venda/sp/sao-paulo/zona-sul/vila-mariana/casa_residencial/")


QA_STATE = {
    "props": {"pageProps": {"initialState": {
        "houses": {
            "9001": {"id": "9001", "rentPrice": 2800, "totalCost": 3700, "condoIptu": 700, "area": 50,
                     "bedrooms": 2, "bathrooms": 1, "parkingSpots": 1, "type": "Apartamento",
                     "neighbourhood": "Pinheiros", "address": {"address": "Rua A", "city": "São Paulo"},
                     "isFurnished": False, "shortRentDescription": "Apartamento com 2 quartos"},
            "9002": {"id": "9002", "rentPrice": 5200, "totalCost": 6500, "area": 80, "bedrooms": 3,
                     "type": "Apartamento", "address": {}},
        },
        "search": {"visibleHouses": {"total": 2, "pages": {"0": ["9002", "9001"]}}},
    }}}
}


class QuintoAndarTests(unittest.TestCase):
    def test_url(self):
        args = search_args(bairro="Pinheiros", quartos=2, preco_max=4000, pets=True, mobiliado=True)
        self.assertEqual(
            quintoandar.build_search_url(args),
            "https://www.quintoandar.com.br/alugar/imovel/pinheiros-sao-paulo-sp-brasil/apartamento/2-quartos/de-0-a-4000-reais/aceita-pets/mobiliado",
        )
        self.assertTrue(quintoandar.build_search_url(search_args(quartos=1)).endswith("/apartamento/1-quarto"))

    def test_search_keeps_page_order_and_filters(self):
        html = f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(QA_STATE)}</script>'
        quintoandar.fetch = lambda url: (url, html)
        payload = quintoandar.search(search_args(limit=24))
        self.assertEqual([r["id"] for r in payload["results"]], ["quintoandar-9002", "quintoandar-9001"])
        payload = quintoandar.search(search_args(total_max=4000, limit=24))
        self.assertEqual([r["id"] for r in payload["results"]], ["quintoandar-9001"])
        self.assertEqual(payload["results"][0]["url"], "https://www.quintoandar.com.br/imovel/9001")
        payload = quintoandar.search(search_args(negocio="venda", limit=24))
        self.assertEqual(payload["results"], [])  # fixture has no sale prices

    def test_detail_finds_nested_node(self):
        node = {"rentPrice": 0, "salePrice": 900000, "remarks": "Reformado", "condoPrice": 1390,
                "iptu": 490, "address": {"street": "Rua A", "neighborhood": "Moema"},
                "amenities": [{"key": "BOX", "text": "Box", "value": "SIM"}, {"key": "ELEVADOR", "value": "NAO"}]}
        data = {"props": {"pageProps": {"x": [{"y": node}]}}}
        self.assertIs(quintoandar.find_listing_node(data), node)


class FilterTests(unittest.TestCase):
    def test_furnished_yes_requires_explicit_flag(self):
        items = [
            {"negocio": "aluguel", "aluguel": 1, "total": 1, "quartos": 1, "area_m2": 1, "vagas": 0, "aceita_pets": None, "mobiliado": m}
            for m in (True, None, False)
        ]
        kept = apply_client_filters(items, search_args(mobiliado=True))
        self.assertEqual([i["mobiliado"] for i in kept], [True])
        kept = apply_client_filters(items, search_args(mobiliado=False))
        self.assertEqual([i["mobiliado"] for i in kept], [None, False])

    def test_slugify(self):
        self.assertEqual(slugify("São Paulo"), "sao-paulo")
        self.assertEqual(slugify("Cambuí"), "cambui")


class CliContractTests(unittest.TestCase):
    def run_cli(self, *argv):
        return subprocess.run([sys.executable, *argv], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)

    def test_unknown_flag_is_json_error(self):
        proc = self.run_cli(".agents/skills/zap-search/cli.py", "search", "--cidade", "X", "--uf", "SP", "--bogus", "1")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stderr)["code"], "BAD_ARG")

    def test_vivareal_neighbourhood_requires_zone(self):
        proc = self.run_cli(".agents/skills/vivareal-search/cli.py", "search", "--cidade", "Campinas", "--uf", "SP", "--bairro", "Cambuí")
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stderr)["code"], "BAD_ARG")


class ScrapeStateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.tmp.name, "vistos.json")
        self.env = {**os.environ, "PROXIMO_AP_STATE": self.state}

    def tearDown(self):
        self.tmp.cleanup()

    def run_tool(self, *argv):
        proc = subprocess.run([sys.executable, "tools/scrape_state.py", *argv], capture_output=True,
                              text=True, encoding="utf-8", cwd=ROOT, env=self.env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def write(self, items):
        path = os.path.join(self.tmp.name, "in.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(items, handle)
        return path

    def test_dedup_across_runs_and_portals(self):
        zap = {"id": "zap-1", "portal": "zap", "url": "https://z/1", "endereco": "Rua A", "area_m2": 50, "aluguel": 3000}
        viva = {"id": "vivareal-9", "portal": "vivareal", "url": "https://v/9", "endereco": "Rua  A", "area_m2": 50, "aluguel": 3010}
        bad = {"id": "x"}
        first = self.run_tool("store", "--results", self.write([zap, viva, bad]))
        self.assertEqual(first["added"], ["zap-1"])
        self.assertEqual(first["skipped"][0]["motivo"], "mesmo imóvel em outro portal")
        self.assertEqual(first["invalid"][0]["faltando"], ["portal", "url"])
        again = self.run_tool("candidates", "--results", self.write([zap]))
        self.assertEqual(again["selected"], [])

    def test_marcar_and_listar(self):
        self.run_tool("store", "--results", self.write([{"id": "qa-1", "portal": "quintoandar", "url": "u"}]))
        self.run_tool("marcar", "--id", "qa-1", "--status", "favorito", "--nota", "varanda boa")
        listed = self.run_tool("listar", "--status", "favorito")
        self.assertEqual(listed["total"], 1)
        self.assertEqual(len(listed["imoveis"][0]["notas"]), 1)


if __name__ == "__main__":
    unittest.main()
