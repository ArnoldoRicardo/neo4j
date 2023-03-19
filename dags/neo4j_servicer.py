import logging
from typing import List

import xmltodict
from airflow.providers.neo4j.hooks.neo4j import Neo4jHook

from neo4j.exceptions import ServiceUnavailable


class App:
    def __init__(self, neo4jHook: Neo4jHook):
        self.driver = neo4jHook.get_conn()

    def close(self):
        self.driver.close()

    def create_protein(self, protein: dict, main_name: str):
        recommended_name = {**protein['recommendedName']}
        alternative_names = []
        for name in protein['alternativeName']:
            alternative_names.append({**name})

        with self.driver.session(database="neo4j") as session:
            result = session.execute_write(self._create_and_return_protein,
                                           recommended_name, alternative_names, main_name)
            for row in result:
                print("Created protein: {p1}".format(p1=row['protein']))
            return result

    @staticmethod
    def _create_and_return_protein(tx, recommended_name: dict, alternative_names: List[dict], main_name: str):
        query = (
            "CREATE (protein:Protein {name: $name})"
            f"CREATE (recommendedName:RecommendedName {{ fullName: '{recommended_name['fullName']}'"
            f", shortName: {recommended_name['shortName']} }})"
        )
        for i, name in enumerate(alternative_names):
            query += f"CREATE (alternativeName{i}:AlternativeName {{ fullName: '{name['fullName']}'"
            if 'shortName' in name:
                query += ", shortName: "
                if type(name['shortName']) == str:
                    query += f"'{name['shortName']}'"
                else:
                    query += f"{name['shortName']}"
            query += "})"

        query += "CREATE (protein)-[:HAD_RECOMMENDED_NAME]->(recommendedName)"

        for i, name in enumerate(alternative_names):
            query += f"CREATE (protein)-[:HAD_ALTERNATIVE_NAME]->(alternativeName{i})"

        query += "RETURN protein"
        result = tx.run(query, name=main_name)
        try:
            return [{"protein": row["protein"]}
                    for row in result]
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=query, exception=exception))
            raise

    def create_genes(self, genes: List[dict], main_name: str):
        for gene in genes['name']:
            self._create_gene(gene, main_name)

    def _create_gene(self, gene, main_name):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_write(self._create_and_return_gene, gene, main_name)
            for row in result:
                print("Created gene: {g1}".format(g1=row['g1']))

    @ staticmethod
    def _create_and_return_gene(tx, gene, main_name):
        query = (
            "MATCH (protein:Protein {name: $main_name})"
            "CREATE (gene:Gene {name: $name, status: $status })"
            "CREATE (protein)-[:FROM_GENE]->(gene)"
            "RETURN gene"
        )
        result = tx.run(query, name=gene['#text'], status=gene['@type'], main_name=main_name)
        try:
            return [{"g1": row["gene"]}
                    for row in result]
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=query, exception=exception))
            raise

    def create_organism(self, organism: dict, name):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_write(self._create_and_return_organism, organism, name)
            for row in result:
                print("Created organism: {o1}".format(o1=row['o1']))

    @staticmethod
    def _create_and_return_organism(tx, organism: dict, main_name: str):
        name = [d for d in organism['name'] if d['@type'] == 'scientific'][0]['#text']
        common_name = [d for d in organism['name'] if d['@type'] == 'common'][0]['#text']

        query = (
            "MATCH (protein:Protein {name: $main_name})"
            "CREATE (organism:Organism {name: $name, taxonomy_id: $taxonomy_id, common_name: $common_name, taxon: $taxon})"
            "CREATE (protein)-[:IN_ORGANISM]->(gene)"
            "RETURN organism"
        )
        result = tx.run(query, name=name,
                        taxonomy_id=organism['dbReference']['@id'],
                        common_name=common_name,
                        taxon=organism['lineage']['taxon'], main_name=main_name)
        try:
            return [{"o1": row["organism"]}
                    for row in result]
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=query, exception=exception))
            raise

    def create_references(self, references: List[dict], main_name: str):
        for reference in references:
            self._create_reference(reference, main_name)

    def _create_reference(self, reference: dict, main_name: str):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_write(self._create_and_return_reference, reference, main_name)
            for row in result:
                if reference['citation']['authorList'].get('person', None):
                    self._create_authors(reference['citation']['authorList']['person'], row['r1']['id'])
                print("Created reference: {r1}".format(r1=row['r1']))

    def _create_authors(self, authors: List[dict], reference: str):
        with self.driver.session(database="neo4j") as session:
            for author in authors:
                result = session.execute_write(self._create_author, author, reference)
                for row in result:
                    print("Created author: {a1}".format(a1=row['a1']))

    @staticmethod
    def _create_author(tx, author: dict, reference: str):
        query = (
            "MATCH (reference:Reference {id: $reference})"
            "CREATE (author:Author {name: $name})"
            "CREATE (reference)-[:HAS_AUTHOR]->(author)"
            "RETURN author"
        )
        result = tx.run(query, name=author['@name'], reference=reference)
        try:
            return [{"a1": row["author"]}
                    for row in result]
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=query, exception=exception))
            raise

    @staticmethod
    def _create_and_return_reference(tx, reference: dict, main_name: str):
        query = (
            "MATCH (protein:Protein {name: $main_name})"
            "CREATE (reference:Reference { id: $id, title: $title, date: $date, volume: $volume, first: $first"
            ", last: $last, source: $source, scope: $scope})"
            "CREATE (protein)-[:HAS_REFERENCE]->(reference)"
            "RETURN reference"
        )

        result = tx.run(query, id=reference['@key'], main_name=main_name, title=reference['citation']['title'],
                        date=reference['citation']['@date'], volume=reference['citation'].get('@volume', 0),
                        first=reference['citation'].get('@first', 0), last=reference['citation'].get('@last', 0),
                        source=reference.get('source', {}).get('tissue', None), scope=reference.get('scope', None))
        try:
            return [{"r1": row["reference"]}
                    for row in result]
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=query, exception=exception))
            raise

    def create_features(self, features: List[dict], main_name: str):
        for feature in features:
            self._create_feature(feature, main_name)

    def _create_feature(self, feature: dict, main_name: str):
        with self.driver.session(database="neo4j") as session:
            result = session.execute_write(self._create_and_return_feature, feature, main_name)
            for row in result:
                print("Created feature: {f1}".format(f1=row['f1']))

    @staticmethod
    def _create_and_return_feature(tx, feature: dict, main_name: str):
        query = (
            "MATCH (protein:Protein {name: $main_name})"
            "CREATE (feature:Feature {type: $type, name: $name})"
            "CREATE (protein)-[:HAS_FEATURE]->(feature)"
            "RETURN feature"
        )
        result = tx.run(query, type=feature['@type'], main_name=main_name,
                        name=feature.get('@description', None))
        try:
            return [{"f1": row["feature"]}
                    for row in result]
        except ServiceUnavailable as exception:
            logging.error("{query} raised an error: \n {exception}".format(
                query=query, exception=exception))
            raise


def parse_entry(entry):
    app = App("bolt://localhost:7687", "neo4j", "123456")

    config = {
        'name': '',
        'created_at': '',
        'modified': '',
        'version': '',
        'dataset': ''
    }

    for key_entry, value in entry.items():
        if type(value) == dict:
            if key_entry == 'protein':
                app.create_protein(value, config['name'])
            elif key_entry == 'gene':
                app.create_genes(value, config['name'])
            elif key_entry == 'organism':
                app.create_organsim(value, config['name'])
        elif type(value) == list:
            if key_entry == 'reference':
                app.create_references(value, config['name'])
            elif key_entry == 'feature':
                app.create_features(value, config['name'])
        else:
            if key_entry == 'name':
                config['name'] = value
            elif key_entry == '@created':
                config['created_at'] = value
            elif key_entry == '@modified':
                config['modified'] = value
            elif key_entry == '@version':
                config['version'] = value
            elif key_entry == '@dataset':
                config['dataset'] = value
            else:
                print(key_entry)
                print(type(value), value)


if __name__ == "__main__":
    with open('data/Q9Y261.xml', 'r') as xml_file:
        data_dict = xmltodict.parse(xml_file.read())
        for key, uniprot in data_dict.items():
            __import__('ipdb').set_trace()
            for key_prot, entry in uniprot.items():
                if type(entry) == dict:
                    parse_entry(entry)
                else:
                    print(key_prot)
                    print(type(entry), entry)
