from flask import Blueprint
import json
from neomodel import config, db

config.DATABASE_URL = 'bolt://neo4j:pw@localhost:7687'

faction_ranks = {'DIE LINKE.': 0,
                 'SPD': 1,
                 'BÜNDNIS 90/DIE GRÜNEN': 2,
                 'CDU/CSU': 3,
                 'FDP': 4,
                 'AFD': 5,
                 'Fraktionslos': 6}


def construct_blueprint(cache):
    blueprint = Blueprint('bt-protocol-rest-api', __name__)

    @blueprint.route('/factions', methods=['GET'])
    @cache.cached()
    def get_factions():
        result = db.cypher_query('MATCH (f:Faction)<-[r:PART_OF]-(m:Mdb) '
                                 'WHERE r.start="2017-10-24" '
                                 'RETURN f.name, f.color, count(m)')[0]

        factions = []
        for entry in result:
            factions.append({'name': entry[0],
                             'color': entry[1],
                             'size': entry[2]})

        return json.dumps(factions)

    @blueprint.route('/pagerank_table', methods=['GET'])
    @cache.cached()
    def get_mdbs():
        result = db.cypher_query('MATCH (m:Mdb)-[:PART_OF]->(f:Faction), '
                                 '(c:Comment)-[:FROM]->(m) '
                                 'RETURN m.first_name, m.last_name, f.name, '
                                 'm.pagerank, m.eigenvector, count(DISTINCT(c))')[0]

        mdbs = []
        for entry in result:
            mdbs.append({'name': f'{entry[0]} {entry[1]}',
                         'faction': entry[2],
                         'pagerank': entry[3],
                         'eigenvector': entry[4],
                         'comments': entry[5]})

        return json.dumps(mdbs)

    @blueprint.route('/comment_table', methods=['GET'])
    @cache.cached()
    def get_comments():
        result = db.cypher_query('MATCH (c:Comment), '
                                 '(c)-[:FROM]->(s:Mdb), '
                                 '(c)-[:TO]->(r:Mdb), '
                                 '(s)-[:PART_OF]->(sf:Faction), '
                                 '(r)-[:PART_OF]->(rf:Faction) '
                                 'RETURN DISTINCT s.first_name, s.last_name, sf.name, '
                                 'r.first_name, r.last_name, rf.name, '
                                 'c.text, c.polarity')[0]

        comments = []
        for entry in result:
            comments.append({'sender': f'{entry[0]} {entry[1]} ({entry[2]})',
                             'receiver': f'{entry[3]} {entry[4]} ({entry[5]})',
                             'comment': entry[6],
                             'polarity': entry[7]})

        return json.dumps(comments)

    @blueprint.route('/comments_chord', methods=['GET'])
    @cache.cached()
    def get_comments_chord():
        # Create zero matrix
        matrix = [[0 for i in range(7)] for j in range(7)]

        result = db.cypher_query('MATCH (c:Comment)-[:FROM]->(s:Mdb), '
                                 '(c)-[:TO]->(r:Mdb), '
                                 '(s)-[:PART_OF]->(sf:Faction), '
                                 '(r)-[:PART_OF]->(rf:Faction) '
                                 'RETURN DISTINCT id(c), sf.name, rf.name')[0]

        for entry in result:
            matrix[faction_ranks[entry[1]]][faction_ranks[entry[2]]] += 1

        # Ignore from/to own faction
        for i in range(7):
            matrix[i][i] = 0

        return json.dumps(matrix)

    @blueprint.route('/polarity_chord', methods=['GET'])
    @cache.cached()
    def get_polarity_chord():
        # Create matrix of empty lists to collect polarities
        matrix = [[list() for i in range(7)] for j in range(7)]

        result = db.cypher_query('MATCH (c:Comment)-[:FROM]->(s:Mdb), '
                                 '(c)-[:TO]->(r:Mdb), '
                                 '(s)-[:PART_OF]->(sf:Faction), '
                                 '(r)-[:PART_OF]->(rf:Faction) '
                                 'RETURN DISTINCT id(c), sf.name, rf.name, c.polarity')[0]

        for entry in result:
            matrix[faction_ranks[entry[1]]][faction_ranks[entry[2]]].append(entry[3])

        # Calculate average
        for i in range(7):
            for j in range(7):
                matrix[i][j] = sum(matrix[i][j]) / len(matrix[i][j])

        # Ignore from/to own faction
        for i in range(7):
            matrix[i][i] = 0

        return json.dumps(matrix)

    @blueprint.route('/polarity_heatmap', methods=['GET'])
    @cache.cached()
    def get_polarity_heatmap():
        result = db.cypher_query('MATCH (c:Comment)-[:FROM]->(s:Mdb),'
                                 '(c)-[:TO]->(r:Mdb), '
                                 '(s)-[:PART_OF]->(sf:Faction), '
                                 '(r)-[:PART_OF]->(rf:Faction) '
                                 'RETURN DISTINCT sf.name, rf.name, avg(c.polarity)')[0]

        points = []
        for faction in faction_ranks:
            points.append({'id': faction})

        for entry in result:
            sender_faction = entry[0]
            receiver_faction = entry[1]
            polarity = float(entry[2])

            for point in points:
                if point['id'] == sender_faction:
                    if sender_faction == receiver_faction:
                        point[receiver_faction] = 0
                    else:
                        point[receiver_faction] = polarity

        return json.dumps(points)

    return blueprint
